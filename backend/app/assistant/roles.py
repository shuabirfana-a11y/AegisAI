import time
from app.assistant.contracts import TaskArtifact
from app.utils.time import utcnow

def call_with_retry(gateway,name,args,context,max_retries,*,deadline=None):
    if not 0<=max_retries<=2:raise ValueError('Retry budget invalid')
    for attempt in range(1,max_retries+2):
        kwargs={'timeout':max(0,deadline-time.monotonic())} if deadline is not None else {}
        result=gateway.invoke(name,args,context,attempt=attempt,**kwargs)
        if result.status!='failed' or not result.retryable or attempt>max_retries or time.monotonic()>=min(context.deadline,deadline or context.deadline):return result
        time.sleep(min(.05*attempt,max(0,context.deadline-time.monotonic())))
    return result

class ToolRole:
    name='Investigation'
    def __init__(self,gateway,context):self.gateway=gateway;self.context=context
    def execute(self,task,accepted):
        started=utcnow();results=[];errors=[];warnings=[];unresolved=[];replans=[]
        deadline=min(self.context.deadline,time.monotonic()+task.timeout)
        calls=task.inputs.get('calls',[])
        if len(calls)>min(8,task.constraints.get('max_calls',8)):raise ValueError('Role call budget exceeded')
        for call in calls:
            name=call['tool'];args=call['args']
            if name not in task.allowed_tools:raise ValueError('Task capability violation')
            r=call_with_retry(self.gateway,name,args,self.context,task.retry_policy.get('max_retries',1),deadline=deadline)
            if r.status=='failed' and task.failure_policy=='replan' and args.get('refresh') and time.monotonic()<deadline:
                # One safe alternative only: reuse the same allowlisted cached service.
                original=r.model_dump(mode='json');r=self.gateway.invoke(name,{**args,'refresh':False},self.context,timeout=deadline-time.monotonic())
                replans.append({'original_request':call,'original_failure':original,'reason':'Live refresh failed; cached scoped fallback','alternative':{'tool':name,'args':{**args,'refresh':False}}})
                warnings.append('Live refresh failed; cached results retain their observation times')
            results.append(r.model_dump(mode='json'));errors.extend(r.errors);warnings.extend(r.warnings)
            if r.status=='no_result':unresolved.append('No result within '+name+' local scope')
            if r.status=='failed':unresolved.append('Tool failed: '+name+' ['+','.join(e.get('code','UNKNOWN') for e in r.errors)+']')
        refs=[];seen=set();claims=[]
        for r in results:
            for ref in r['evidence_refs']:
                key=(ref.get('evidence_id'),ref.get('raw_document_id'),str(ref.get('locator')))
                if key not in seen:seen.add(key);refs.append(ref)
            if r['tool']=='get_claims':
                for c in r['data'].get('items',[]):
                    # CONFIRMED-but-stale is never passed as a current confirmation.
                    claims.append({**c,'verification_status':c['verification_status'] if c.get('trusted') or c['verification_status']!='CONFIRMED' else 'INSUFFICIENT_EVIDENCE'})
                    if c['verification_status']=='CONFIRMED' and not c.get('trusted'):warnings.append('Stored confirmation is not currently trusted: '+str(c['id']))
            if r['tool']=='get_verification_result':
                c=r['data'].get('claim')
                if c:claims.append({**c,'trusted':r['data'].get('trusted',False),'verification_status':c['verification_status'] if r['data'].get('trusted') or c['verification_status']!='CONFIRMED' else 'INSUFFICIENT_EVIDENCE'})
        failures=sum(r['status']=='failed' for r in results)
        required=set(task.inputs.get('required_tools',[]))
        required_failed=any(r['tool'] in required and r['status']=='failed' for r in results)
        status='failed' if required_failed or (results and failures==len(results)) else 'partial' if errors or warnings or unresolved else 'success'
        return TaskArtifact(task_id=task.task_id,agent=self.name,status=status,
            result={'tool_results':results,'replans':replans,'capability':'deterministic tool role; no LLM inference'},claims=claims,evidence_refs=refs,
            warnings=list(dict.fromkeys(warnings)),errors=errors,unresolved=unresolved,trace_id=self.context.trace_id,started_at=started,finished_at=utcnow())

class InvestigationRole(ToolRole):name='Investigation'
class VerificationRole(ToolRole):name='Verification'
class SecurityAnalysisRole(ToolRole):
    name='SecurityAnalysis'
    def execute(self,task,accepted):
        started=utcnow();refs=[];claims=[];warnings=[];unresolved=[]
        for dep in task.dependencies:
            a=accepted[dep];refs.extend(a.evidence_refs);claims.extend(a.claims);warnings.extend(a.warnings);unresolved.extend(a.unresolved)
        return TaskArtifact(task_id=task.task_id,agent=self.name,status='partial' if warnings or unresolved else 'success',
            result={'source_tasks':task.dependencies,'capability':'deterministic security synthesis; no generation model'},claims=claims,evidence_refs=refs,
            warnings=list(dict.fromkeys(warnings)),unresolved=unresolved,trace_id=self.context.trace_id,started_at=started,finished_at=utcnow())
