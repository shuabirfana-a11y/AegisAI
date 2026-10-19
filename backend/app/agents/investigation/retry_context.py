"""Identify the rejected object for repair without changing or executing it."""
from app.llm.schemas import strict_json
from app.agents.investigation.roles import ROLES

MAX_REJECTED_CONTEXT_BYTES = 8192


def rejected_context(diagnostic):
    result={'trust_level':'UNTRUSTED_MODEL_OUTPUT_DATA',
            'registered_task_requirements':[],'context_status':'UNAVAILABLE'}
    if diagnostic is None:return result
    if diagnostic.redacted or diagnostic.truncated:
        return {**result,'context_status':'UNAVAILABLE_REDACTED_OR_TRUNCATED'}
    if len(diagnostic.raw_output.encode('utf8'))>MAX_REJECTED_CONTEXT_BYTES:
        return {**result,'context_status':'UNAVAILABLE_SIZE_LIMIT'}
    try:candidate=strict_json(diagnostic.raw_output)
    except (ValueError,TypeError,RecursionError):
        return {**result,'context_status':'UNAVAILABLE_INVALID_JSON'}
    if not isinstance(candidate,dict):return {**result,'context_status':'UNAVAILABLE_NOT_OBJECT'}
    # Registry conditions are already required by the unchanged Schema/validator.
    # The untrusted candidate supplies identity only, never authority or facts.
    tasks=candidate.get('tasks')
    if isinstance(tasks,list):
        for index,task in enumerate(tasks[:16]):
            if not isinstance(task,dict):continue
            role=task.get('type')
            if isinstance(role,str) and role in ROLES and task.get('task_type')=='tool_sequence':
                result['registered_task_requirements'].append({
                    'path':f'$.tasks[{index}].acceptance_criteria',
                    'task_id':task.get('task_id'),'role':role,
                    'minimum_conditions':sorted(ROLES[role].criteria)})
    return {**result,'context_status':'AVAILABLE','rejected_candidate':candidate}
