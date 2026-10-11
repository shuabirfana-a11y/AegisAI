from datetime import datetime,timedelta,timezone
from app.assistant.router import route
from app.assistant.contracts import TaskContract
from app.assistant.graph import run_graph,failed
from app.assistant.handoff import validate_handoff
from app.assistant.roles import InvestigationRole,VerificationRole,SecurityAnalysisRole
from app.assistant.gate import integrate
from app.tooling.gateway import ToolGateway

class Orchestrator:
    """One bounded coordinator and three deterministic tool roles, explicitly model-free."""
    def __init__(self,context,*,gateway=None,on_stage=None):
        self.context=context;self.gateway=gateway or ToolGateway();self.on_stage=on_stage or (lambda **x:None)
        self.roles={r.name:r(self.gateway,context) for r in (InvestigationRole,VerificationRole,SecurityAnalysisRole)}
    def _execute(self,task,accepted):
        self.on_stage(status='VERIFYING' if task.task_type=='Verification' else 'WAITING_TOOL',event={'task_id':task.task_id,'state':'started'})
        artifact=self.roles[task.task_type].execute(task,accepted)
        self.on_stage(event={'task_id':task.task_id,'state':artifact.status,'warnings':artifact.warnings,'errors':artifact.errors})
        return artifact
    def run(self,request):
        routing=route(request.question,target=request.target,asset_id=request.asset_id,mode=request.mode)
        if request.realtime:routing.update(path='deep',retrieval='hybrid',realtime_requested=True)
        self.on_stage(status='PLANNING',route=routing)
        if routing['blocked']:
            return {'route':routing,'plan':[],'artifacts':[],'gate':{'status':'FAILED','reason':'Requested execution is outside the allowlisted intelligence tools'},
                'answer':'该请求包含越权执行或泄露指令，已拒绝。可以查询漏洞、来源证据和自己的资产风险。','evidence_refs':[],
                'warnings':['No tool executed'],'unresolved':['Request outside supported scope'],'capability':'deterministic_only'}
        if routing['asset']:
            rootcalls=[{'tool':'get_asset_risks','args':{'asset_id':str(request.asset_id)} if request.asset_id else {}}]
        elif routing['targets']:rootcalls=[{'tool':'get_vulnerability','args':{'target':routing['targets'][0]}}]
        elif routing['product']:rootcalls=[{'tool':'search_vulnerabilities','args':{'product':routing['product'],'limit':3,'high_severity':routing['high_severity'],**({'days':routing['days']} if routing['days'] else {})}}]
        elif routing['retrieval']=='semantic':rootcalls=[{'tool':'semantic_search','args':{'query':request.question}}]
        elif '系统状态' in request.question or 'system status' in request.question.casefold():rootcalls=[{'tool':'get_system_status','args':{}}]
        else:rootcalls=[{'tool':'get_recent_intelligence','args':{'days':routing['days'] or 90,'ai_relevance':'relevant','limit':20,'high_severity':routing['high_severity']}}]
        if routing['path']=='deep' and not any(c['tool']=='semantic_search' for c in rootcalls):
            rootcalls.append({'tool':'semantic_search','args':{'query':request.question,'limit':3}})
        if routing['path']=='fast' and routing['targets']:rootcalls.append({'tool':'get_claims','args':{'target':routing['targets'][0],'limit':100}})
        root=TaskContract(task_id='root',goal='Fetch bounded primary intelligence or owner assets',task_type='Investigation',inputs={'calls':rootcalls,'required_tools':[rootcalls[0]['tool']]},allowed_tools=[c['tool'] for c in rootcalls])
        self.on_stage(status='RUNNING',plan=[root.model_dump(mode='json')])
        first=self._execute(root,{})
        try:validate_handoff(root,first,self.context.trace_id,{},evidence_attested=self.context.evidence_attested,claims_attested=self.context.claims_attested)
        except ValueError:
            rejected=failed(root,self.context.trace_id,'HANDOFF_REJECTED');rejected.unresolved=first.unresolved
            rejected.errors.extend(first.errors);rejected.warnings=first.warnings
            return self._finish(routing,[root],[rejected])
        tasks=[root]
        if routing['path']=='deep':
            targets=list(routing['targets']);warnings=[]
            if routing['product'] and not targets and not routing['asset']:
                targets=[r['canonical_id'] for r in first.result['tool_results'][0].get('data',{}).get('items',[])][:3]
                first.warnings.append('Product investigation is bounded to three local candidates; not exhaustive')
            if routing['asset']:
                items=first.result['tool_results'][0].get('data',{}).get('items',[])
                filtered=[]
                cutoff=datetime.now(timezone.utc)-timedelta(days=routing['days']) if routing['days'] else None
                for r in items:
                    date=r.get('published_at')
                    if cutoff and date and datetime.fromisoformat(date.replace('Z','+00:00'))<cutoff:continue
                    if routing['high_severity'] and r.get('severity') not in ('high','critical','unknown',None):continue
                    filtered.append(r)
                first.result['tool_results'][0]['data']['items']=filtered
                targets=list(dict.fromkeys(r['canonical_id'] for r in filtered if r.get('canonical_id') and r.get('match_status')!='NOT_AFFECTED'))[:3]
                if len(set(r.get('canonical_id') for r in items))>3:warnings.append('Investigation is bounded to three local candidate vulnerabilities; remaining inventory requires another run')
                first.warnings.extend(warnings)
            leaves=[]
            for index,target in enumerate(targets):
                investigation_id='investigate-'+str(index)
                calls=[{'tool':'investigate_vulnerability','args':{'target':target,'refresh':request.realtime}},
                    {'tool':'relation_query','args':{'target':target,'limit':100}}]
                tasks.append(TaskContract(task_id=investigation_id,goal='Collect vendor/PoC/patch/EPSS/KEV and scoped relations',task_type='Investigation',
                    inputs={'calls':calls},dependencies=['root'],allowed_tools=[c['tool'] for c in calls],failure_policy='replan'))
                verification_id='verify-'+str(index)
                tasks.append(TaskContract(task_id=verification_id,goal='Read current scoped deterministic verification and evidence',task_type='Verification',
                    inputs={'calls':[{'tool':'get_claims','args':{'target':target,'limit':100}}]},dependencies=[investigation_id],allowed_tools=['get_claims']))
                leaves.append(verification_id)
            # Every accepted branch is a dependency of analysis; failed evidence cannot silently disappear.
            tasks.append(TaskContract(task_id='analysis',goal='Synthesize accepted structured artifacts with uncertainty preserved',task_type='SecurityAnalysis',
                inputs={'question':request.question},dependencies=['root',*leaves],allowed_tools=[]))
            self.on_stage(plan=[t.model_dump(mode='json') for t in tasks])
            artifacts=run_graph(tasks,self._execute,self.context.trace_id,deadline=self.context.deadline,initial={'root':first},
                evidence_attested=self.context.evidence_attested,claims_attested=self.context.claims_attested)
        else:artifacts=[first]
        return self._finish(routing,tasks,artifacts)
    def _finish(self,routing,tasks,artifacts):
        with self.context.lock:
            gate=integrate(artifacts,claims_attested=set(self.context.claims_attested),evidence_attested=set(self.context.evidence_attested))
        refs=[];seen=set();warnings=['Generation model unavailable: response is deterministic tool synthesis'];unresolved=[];claims=[]
        related_vulns=[];related_assets=[];facts=[];risks=[];narratives=[]
        for a in artifacts:
            warnings.extend(a.warnings);unresolved.extend(a.unresolved);claims.extend(a.claims)
            for r in a.evidence_refs:
                key=(r.get('evidence_id'),r.get('claim_revision'),r.get('raw_document_id'),str(r.get('locator')))
                if key not in seen:seen.add(key);refs.append(r)
            for result in a.result.get('tool_results',[]):
                data=result.get('data',{});tool=result['tool']
                if tool in ('get_vulnerability','relation_query'):related_vulns.append({'id':str(data.get('id')),'canonical_id':data.get('canonical_id'),'title':data.get('title'),'published_at':data.get('published_at')})
                if tool=='get_asset_risks':
                    risks.extend(data.get('items',[]))
                    related_assets.extend({'asset_id':r['asset_id'],'name':r.get('asset_name'),'is_demo':r.get('is_demo')} for r in data.get('items',[]))
                if tool=='semantic_search':narratives.extend(data.get('items',[]))
                if tool in ('get_recent_intelligence','search_vulnerabilities'):related_vulns.extend(data.get('items',[]))
        for c in claims:
            if c.get('trusted') and c.get('verification_status')=='CONFIRMED':
                facts.append({'claim_id':str(c['id']),'claim_revision':c['revision'],'predicate':c['predicate'],'claim_type':c['claim_type'],
                    'scope_key':c['scope_key'],'value':c['value_json'],'verification_status':'CONFIRMED'})
        if routing.get('days') and risks:
            dated={v['canonical_id']:v.get('published_at') for v in related_vulns if v.get('canonical_id')}
            cutoff=datetime.now(timezone.utc)-timedelta(days=routing['days']);kept=[]
            for r in risks:
                date=r.get('published_at') or dated.get(r.get('canonical_id'))
                if date:
                    try:
                        when=datetime.fromisoformat(date.replace('Z','+00:00'))
                        if when<cutoff:continue
                    except (ValueError,TypeError):date=None
                if date is None:r={**r,'publication_window_status':'UNKNOWN'}
                kept.append(r)
            risks=kept;warnings.append(str(routing['days'])+'-day scope uses vulnerability publication time; candidates with unknown dates remain marked UNKNOWN')
        if gate['status'] in ('PASS','PASS_WITH_WARNINGS'):
            answer='已完成范围内查询；以下为带来源的结构化结果。未核实内容保留为来源陈述，缺失结果不等于不存在。'
            if not refs:answer='本次范围内未获得可支持结论的证据，暂不作事实判断。';facts=[];warnings.append('ABSTENTION: no supporting evidence')
        else:
            answer='存在来源冲突或资产匹配不确定性，需要人工复核。以下证据和候选项供复核，不作确定影响或安全结论。' if gate['status']=='HUMAN_REVIEW_REQUIRED' else '必要任务或证据校验未通过，暂不生成事实答案。'
            facts=[]
        def unique(rows,key):return list({str(r.get(key)):r for r in rows}.values())
        return {'route':routing,'plan':[t.model_dump(mode='json') for t in tasks],'artifacts':[a.model_dump(mode='json') for a in artifacts],
            'gate':gate,'answer':answer,'facts':unique(facts,'claim_id'),'asset_candidates':risks,'narrative_candidates':narratives,
            'related_vulnerabilities':unique(related_vulns,'canonical_id'),'related_assets':unique(related_assets,'asset_id'),
            'evidence_refs':refs,'warnings':list(dict.fromkeys(warnings)),'unresolved':list(dict.fromkeys(unresolved)),
            'capability':'DETERMINISTIC_TOOL_ROLES + REAL_LOCAL_SEMANTIC_MODEL; NO GENERATION_MODEL',
            'coverage':'Bounded local data and owner inventory; source assertions do not prove completeness'}
