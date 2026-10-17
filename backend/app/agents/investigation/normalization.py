"""Literal input normalization. No model, retrieval, inventory or answer access."""
import re
from copy import deepcopy
from typing import Literal
from pydantic import Field
from app.runtime.contracts import FrozenModel,json_bytes

NORMALIZER_VERSION='question-normalizer-v1'
COMPONENTS=('langchain-core','langchain','transformers','pytorch','torch','vllm','mlflow')
LABEL_KEYS={'expected_answer','ground_truth','gold_answer','review_status','annotator','reviewer'}
CVE=re.compile(r'\bCVE-\d{4}-\d{4,}\b',re.I)
VERSION=r'([0-9]+(?:\.[0-9]+){1,3}(?:[a-zA-Z+-](?:[a-zA-Z0-9.+-]*[a-zA-Z0-9])?)?)(?!\.[0-9])'


class NormalizedQuestion(FrozenModel):
    normalizer_version:Literal['question-normalizer-v1']=NORMALIZER_VERSION
    objective:str=Field(min_length=1,max_length=2000)
    vulnerability_id:str|None=None
    targets:tuple[str,...]=()
    component:dict|None=None
    version:str|None=None
    asset_context:dict=Field(default_factory=dict)
    task_type:Literal['vulnerability_fact','version_impact','asset_risk','evidence_conflict']
    input_status:Literal['READY','INPUT_REQUIRED','AMBIGUOUS']
    missing_fields:tuple[str,...]=()
    warnings:tuple[str,...]=()
    provenance:dict[str,str]=Field(default_factory=dict)


def reject_labels(value):
    if isinstance(value,dict):
        if LABEL_KEYS&set(value):raise ValueError('LABEL_METADATA_FORBIDDEN')
        for v in value.values():reject_labels(v)
    elif isinstance(value,(list,tuple)):
        for v in value:reject_labels(v)


def explicit_versions(question,name):
    pattern=r'(?<![\w-])'+re.escape(name)+r'(?![\w-])\s+(?:(?:版本|version)\s*[:：]?\s*)?v?'+VERSION
    result=[]
    for match in re.finditer(pattern,question,re.I):
        # Evaluate the candidate's own clause, never an arbitrary cross-sentence window.
        boundaries=list(re.finditer(r'[。!?？;；]|\.(?![0-9])',question[:match.start()]))
        start=boundaries[-1].end() if boundaries else 0
        before=question[start:match.start()].casefold()
        after=question[match.end():match.end()+40].casefold()
        advisory=re.search(r'affected\s+(?:range|versions?)|(?:fixed|patched)\s+(?:version|in)|applies\s+to|修复版本|受影响版本|影响范围',before)
        range_end=re.match(r'\s*(?:\b(?:to|through|until|and|or)\b|至|到|以下|之前|[-–—~～]|\.{2,})',after)
        range_inside=re.search(r'[0-9]\.[0-9].*-[0-9]\.[0-9]',match.group(1))
        deployment=re.search(r'\b(?:my|deployed|deployment|installed|running)\b|我的|部署|安装|运行',before)
        clause=question[start:]
        applicability_question=('?' in clause or '？' in clause) and re.search(r'是否|影响|受|affected|affect|vulnerable',clause,re.I)
        if (deployment or applicability_question) and not (advisory or range_end or range_inside):
            result.append(match.group(1))
    return list(dict.fromkeys(result))


def normalize_question(question,values=None,bindings=None,*,extract_literals=True):
    values=deepcopy(values or {});bindings=deepcopy(bindings or {})
    reject_labels(values);reject_labels(bindings)
    json_bytes([question,values,bindings],65536)
    provenance={};warnings=[];q=question.casefold()
    targets=values.get('targets')
    if targets is None:targets=[]
    if not isinstance(targets,(list,tuple)):raise ValueError('NORMALIZATION_INVALID_TARGETS')
    if values.get('target'):targets=[values['target'],*targets]
    literal_targets=tuple(dict.fromkeys(x.upper() for x in CVE.findall(question))) if extract_literals else ()
    if targets:
        if not all(isinstance(t,str) for t in targets):raise ValueError('NORMALIZATION_INVALID_TARGETS')
        targets=tuple(dict.fromkeys(targets));provenance['vulnerability_id']='INPUT_CONTEXT'
        if literal_targets and not set(literal_targets)<=set(targets):
            raise ValueError('NORMALIZATION_INPUT_CONFLICT: target')
    else:targets=literal_targets;provenance['vulnerability_id']='QUESTION_EXPLICIT_CVE' if targets else 'MISSING'
    raw_component=values.get('component')
    component=dict(raw_component) if isinstance(raw_component,dict) else \
        {'name':raw_component,'package_name':raw_component,'ecosystem':values.get('ecosystem')} if raw_component else None
    found=[n for n in COMPONENTS if re.search(r'(?<![\w-])'+re.escape(n)+r'(?![\w-])',question,re.I)] if extract_literals else []
    if component is None and len(found)==1:
        component={'name':found[0]};provenance['component']='QUESTION_EXPLICIT_COMPONENT'
    elif component is not None:provenance['component']='INPUT_CONTEXT'
    elif len(found)>1:warnings.append('MULTIPLE_COMPONENTS');provenance['component']='AMBIGUOUS'
    else:provenance['component']='MISSING'
    if component is not None:
        if not isinstance(component.get('name'),str):raise ValueError('NORMALIZATION_INVALID_COMPONENT')
        for key in ('package_name','ecosystem','purl'):
            if key in values and key not in component:component[key]=values[key]
        if extract_literals and raw_component is not None:
            names={component['name'].casefold(),str(component.get('package_name') or '').casefold()}
            # Unknown scoped package identifiers may have a different display
            # name. Without an alias resolver this layer cannot declare conflict.
            if names&set(COMPONENTS) and any(n not in names and explicit_versions(question,n) for n in found):
                raise ValueError('NORMALIZATION_INPUT_CONFLICT: component')
    # CVSS versions, range operators and bare version numbers are not deployment observations.
    literal_versions=[]
    if component and extract_literals:literal_versions=explicit_versions(question,component['name'])
    explicit_version='version' in values or isinstance(raw_component,dict) and 'version' in raw_component
    if 'version' in values and isinstance(raw_component,dict) and 'version' in raw_component and values['version']!=raw_component['version']:
        raise ValueError('NORMALIZATION_INPUT_CONFLICT: version')
    version=values.get('version',component.get('version') if component else None)
    if version is not None and not isinstance(version,str):raise ValueError('NORMALIZATION_INVALID_VERSION')
    if version is not None and version.casefold() in ('','unknown','未知'):version=None
    if explicit_version:
        provenance['version']='INPUT_CONTEXT'
        if version is not None and literal_versions and set(literal_versions)!={version}:
            raise ValueError('NORMALIZATION_INPUT_CONFLICT: version')
    elif len(literal_versions)==1:
        version=literal_versions[0];provenance['version']='QUESTION_EXPLICIT_COMPONENT_VERSION'
    elif len(literal_versions)>1:
        warnings.append('MULTIPLE_VERSIONS');version=None;provenance['version']='AMBIGUOUS'
    else:provenance['version']='MISSING'
    if component is not None and (explicit_version or version is not None):component['version']=version
    asset={k:bindings[k] for k in ('asset_id','component_id','snapshot_id') if bindings.get(k)}
    if asset:provenance['asset_context']='ACTUAL_ASSET_BINDING'
    for key in ('environment','exposure','criticality'):
        if key in values:asset[key]=values[key]
    conflict=any(w in q for w in ('冲突','矛盾','conflict','contradict'))
    risk=any(w in q for w in ('风险','优先级','risk','priority'))
    applicability=any(w in q for w in ('是否','受影响','affected','受','我的','my '))
    # Supplied scope indicates deployment analysis. A CVSS-version overview does not.
    task_type='evidence_conflict' if conflict else 'asset_risk' if risk else \
        'version_impact' if asset.get('asset_id') or component and (version is not None or applicability) else 'vulnerability_fact'
    missing=[]
    if not targets:missing.append('vulnerability_id')
    if task_type in ('version_impact','asset_risk'):
        if component is None:missing.append('component')
        if not version:missing.append('version')
        if not asset.get('asset_id'):missing.append('asset_context')
    return NormalizedQuestion(objective=question,vulnerability_id=targets[0] if len(targets)==1 else None,
        targets=targets,component=component,version=version,asset_context=asset,task_type=task_type,
        input_status='AMBIGUOUS' if warnings else 'INPUT_REQUIRED' if missing else 'READY',
        missing_fields=tuple(missing),warnings=tuple(warnings),provenance=provenance)
