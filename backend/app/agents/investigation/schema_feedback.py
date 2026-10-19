"""Bounded diagnostics from the exact generation schema; never repairs a candidate."""
import json
from itertools import islice
from pydantic import ValidationError
from app.llm.gateway import prepare_schema
from app.llm.schemas import strict_json
from app.planner.schemas import ValidationIssue


def schema_feedback(raw, request, output_model):
    schema, _, _, validator = prepare_schema(request, output_model)
    value = strict_json(raw)
    names = set()

    def properties(node):
        if isinstance(node, dict):
            names.update(node.get('properties', {}))
            for child in node.values():properties(child)
        elif isinstance(node, list):
            for child in node:properties(child)
    properties(schema)

    def path(parts):
        return '$' + ''.join(f'[{p}]' if isinstance(p, int) else
                             '.' + (p if p in names else '<unknown-field>') for p in parts)

    def resolve(node):
        if '$ref' in node:
            target = schema
            for part in node['$ref'][2:].split('/'):
                target = target[part.replace('~1','/').replace('~0','~')]
            return target
        return node

    def leaves(error):
        # Explain only the matching tool branch, not impossible sibling tools.
        if error.validator == 'anyOf' and isinstance(error.instance, dict):
            branches = error.schema['anyOf']; selected = []
            for index, branch in enumerate(branches):
                props = resolve(branch).get('properties', {})
                discriminators = {key:props[key]['const'] for key in ('name','task_type')
                                  if key in props and 'const' in props[key]}
                if discriminators and all(error.instance.get(k)==v for k,v in discriminators.items()):
                    selected.append(index)
            if selected:
                for child in error.context:
                    if child.schema_path and child.schema_path[0] in selected:yield from leaves(child)
                return
        yield error

    def json_type(item):
        if item is None:return 'null'
        if isinstance(item, bool):return 'boolean'
        if isinstance(item, dict):return 'object'
        if isinstance(item, list):return 'array'
        if isinstance(item, str):return 'string'
        return 'integer' if isinstance(item, int) else 'number'

    issues=[]
    for root in islice(validator.iter_errors(value), 64):
        for error in leaves(root):
            keyword=error.validator; parts=list(error.absolute_path)
            fields=[k for k in error.validator_value if k not in error.instance] if keyword=='required' else [None]
            for field in fields:
                details={'schema_keyword':keyword, 'requirement':{
                    'required':'Supply the required field explicitly.',
                    'type':'Use the declared JSON type.',
                    'enum':'Use an allowed member of the formal schema enum.',
                    'const':'Use the exact supplied scoped argument.',
                }.get(keyword,'Satisfy the existing formal schema constraint.')}
                if keyword=='type':details.update(expected_type=error.validator_value,actual_type=json_type(error.instance))
                item=ValidationIssue(code='SCHEMA_FIELD_'+str(keyword).upper(),
                    path=path(parts+([field] if field else [])),message=json.dumps(details,sort_keys=True))
                if item not in issues:issues.append(item)
                if len(issues)>=32:
                    return (*issues,ValidationIssue(code='SCHEMA_FEEDBACK_LIMIT',path='$',
                        message='Diagnostic limit reached; all schema constraints still apply.'))
    if not issues:
        # Pydantic may reject an otherwise JSON-schema-valid candidate. Do not
        # expose its raw input, custom exception text, or candidate instructions.
        try:output_model.model_validate_json(raw,strict=True)
        except ValidationError as exc:
            for error in exc.errors(include_input=False,include_context=False,include_url=False)[:32]:
                issues.append(ValidationIssue(code='SCHEMA_FIELD_MODEL',path=path(error['loc']),
                    message=json.dumps({'schema_keyword':error['type'],
                        'requirement':'Satisfy the existing model field contract.'},sort_keys=True)))
    return tuple(issues)
