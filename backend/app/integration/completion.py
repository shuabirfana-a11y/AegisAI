"""Execution completeness distinguishes recoverable data gaps from program errors."""
from app.integration.rules_common import check,finish
from app.integration.profiles import is_overview

RECOVERABLE=frozenset({'NOT_FOUND','NO_RESULT','TASK_TIMEOUT','RUN_TIMEOUT','TOOL_TIMEOUT','DEPENDENCY_BLOCKED','INPUT_REQUIRED','TOOL_UNAVAILABLE','NETWORK_ERROR','RATE_LIMITED'})
def check_completion(c):
    issues=[];overview=is_overview(c)
    for stage,art in (('investigation',c.investigation),('verification',c.verification),('analysis',c.analysis)):
        if art is None and (stage!='analysis' or not overview):issues.append(check('completion','REQUIRED_ARTIFACT_MISSING','Missing '+stage,'REPLAN',refs=(stage,)))
    for t in c.tasks:
        ref=(t.run_id,t.task_id)
        if t.run_status=='cancelled' or 'RUN_CANCELLED' in t.error_codes:
            issues.append(check('completion','EXECUTION_CANCELLED','Cancelled execution cannot pass','FATAL',refs=ref));continue
        if t.status=='FAILED' and (not t.error_codes or set(t.error_codes)-RECOVERABLE):
            issues.append(check('completion','EXECUTION_FAILED','Program/protocol failure or unclassified execution error','FATAL',refs=(*ref,*t.error_codes)));continue
        if t.run_status in ('queued','running'):
            issues.append(check('completion','RUN_NOT_TERMINAL','Source run is still changing','REPLAN',refs=ref))
        acceptable=t.status=='SUCCESS'
        # Bounded overview may faithfully report domain abstention; partial tool
        # execution is never covered by this exception.
        if overview and t.status=='WAITING_REVIEW' and not t.error_codes:
            art=next((a for a in (c.investigation,c.verification,c.analysis) if a and a.run_id==t.run_id and a.task_id==t.task_id),None)
            acceptable=bool(art and not getattr(art,'partial_result',False) and getattr(art,'status',None)!='PARTIAL')
        if not acceptable:
            issues.append(check('completion','REQUIRED_TASK_INCOMPLETE' if t.required else 'OPTIONAL_TASK_INCOMPLETE',
                'Required task did not complete' if t.required else 'Independent optional source unavailable',
                'REPLAN' if t.required else 'NONE',warning=not t.required,refs=ref))
    for art in (c.investigation,c.verification,c.analysis):
        if art and (getattr(art,'partial_result',False) or getattr(art,'status',None)=='PARTIAL' or not getattr(art,'coverage_complete',True)):
            issues.append(check('completion','REQUIRED_PARTIAL_RESULT','Partial essential result is not complete','REPLAN',refs=(art.artifact_id,)))
    return finish('completion',issues)
