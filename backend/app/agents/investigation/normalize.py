"""Pure projection of observed data. No model, database or tool invocation."""
import json
from itertools import combinations
from uuid import UUID
from app.agents.artifacts import validate_artifact_json
from app.agents.investigation.schemas import InvestigationArtifact
from app.runtime.contracts import TaskInput, TaskState, WIRE_LIMIT, ARTIFACT_LIMIT, json_bytes
from app.runtime.executor import evidence, evidence_reference
from app.tooling.attestation import evidence_key
from app.enrichment.rules import compare_claims

def _copy(value):
    return json.loads(json_bytes(value,WIRE_LIMIT))

def _credible(ref):
    return (ref.get('authority_level') in ('official','authoritative') and ref.get('is_current') is True
        and all(ref.get(k) is not None and ref.get(k) != '' for k in ('source_id','raw_document_id','url','locator')))

def normalize_investigation(task, outcome, dependencies=()):
    artifact=outcome.artifact
    validate_artifact_json(artifact)
    if artifact.task_id != task.task_id or tuple(a.task_id for a in dependencies)!=task.dependencies:
        raise ValueError('Investigation dependency identity mismatch')
    if any(a.run_id!=artifact.run_id or a.status!=TaskState.SUCCESS for a in dependencies):
        raise ValueError('Investigation dependency run or state mismatch')
    if len({a.artifact_id for a in dependencies})!=len(dependencies):
        raise ValueError('Duplicate dependency artifact')
    inputs=TaskInput.model_validate(task.input_data)
    refs={}; outputs=[]; ref_targets={}
    for dep in dependencies:
        for ref in dep.evidence: refs.setdefault(evidence_key(ref),_copy(ref))
        outputs.extend(_copy(dep.result.get('outputs',[])))
    for receipt in outcome.receipts:
        json_bytes(receipt.envelope.data,WIRE_LIMIT)
        for ref in receipt.envelope.evidence_refs:
            key=evidence_key(ref);refs.setdefault(key,_copy(ref))
            if receipt.envelope.status in ('success','partial') and receipt.arguments.get('target') and receipt.name in (
                'get_vulnerability','get_evidence','get_claims','relation_query','inspect_component_version'):
                ref_targets.setdefault(key,set()).add(receipt.arguments['target'])
        outputs.append({'tool':receipt.name,'status':receipt.envelope.status,'data':_copy(receipt.envelope.data)})
    targets={step.arguments['target'] for step in inputs.steps if step.arguments.get('target')}
    values={'artifact_id':artifact.artifact_id,'run_id':artifact.run_id,'task_id':artifact.task_id,
        'runtime_status':artifact.status,'confidence':artifact.confidence,'evidence':list(refs.values()),
        'tool_calls':_copy(artifact.tool_calls),'dependency_artifact_ids':tuple(str(a.artifact_id) for a in dependencies),
        'uncertainties':list(artifact.unresolved_questions),'status':'INSUFFICIENT_EVIDENCE'}
    details=[]; claims=[]; conflicts=[]; failed=[]; findings=[]
    for result in outputs:
        data=result.get('data'); name=result.get('tool')
        if result.get('status')=='failed':
            continue
        if not isinstance(data,dict):continue
        if name=='get_vulnerability' and data.get('canonical_id'):
            if targets and data.get('canonical_id') not in targets and data.get('id') not in targets:
                raise ValueError('Investigation target differs from observed vulnerability')
            details.append(data)
        if name=='search_vulnerabilities':findings.extend(data.get('items',[]))
        if name=='get_asset':values['asset']=data
        if name=='inspect_component_version':
            values['version_match']=data
            values['component']=data.get('component')
        intel=data.get('intelligence',data if name=='relation_query' else {})
        if name=='relation_query' and data.get('canonical_id'):
            if targets and data.get('canonical_id') not in targets and data.get('id') not in targets:
                raise ValueError('Relation target differs from investigation')
            details.append(data)
        if isinstance(intel,dict):
            for kind,field in [('pocs','poc_candidates'),('patches','patch_information')]:
                items=intel.get(kind,[])
                if isinstance(items,dict):items=items.get('items',[])
                values.setdefault(field,[]).extend(_copy(items))
            items=intel.get('claims',[])
            claims.extend(items.get('items',[]) if isinstance(items,dict) else items)
            conflicts.extend(c for c in intel.get('conflicts',[]) if c.get('status')=='open')
        if name in ('get_claims','get_evidence'):
            findings.extend({'tool':name,'data':_copy(row),'observation_only':True} for row in data.get('items',[]))
        if name in ('get_evidence','get_vulnerability') and isinstance(data.get('candidate_reference'),dict):
            values.setdefault('patch_information',[]).append(_copy(data['candidate_reference']))
        if name=='get_claims':claims.extend(data.get('items',[]))
    if details:
        ids={d.get('id') or d['canonical_id'] for d in details}
        if len(ids)!=1:raise ValueError('Multiple targets cannot share a single investigation artifact')
        primary=next((d for d in details if 'cvss_assessments' in d),details[0])
        values.update(vulnerability_id=primary.get('id'),canonical_id=primary.get('canonical_id'),
            description=primary.get('description'),affected_versions=primary.get('affected_versions',[]),
            cvss=primary.get('cvss_assessments',[]),cwe=primary.get('cwe',[]))
        values['fixed_versions']=[{k:r.get(k) for k in ('id','fixed','package_identifier_id','source_id',
            'observation_id','source_key','is_current','verification_status')} for r in primary.get('affected_versions',[]) if r.get('fixed')]
    values['findings']=findings
    for candidate in values.get('poc_candidates',[]):
        candidate['observed_status']=candidate.get('status')
        candidate['status']='CANDIDATE'
    wanted=targets|{str(d[k]) for d in details for k in ('id','canonical_id') if d.get(k)}
    associated_raw={str(d['id']) for item in details for d in item.get('source_documents',[]) if d.get('id')}
    def relevant(key,ref):
        return bool(ref_targets.get(key,set()) & wanted or str(ref.get('vulnerability_id')) in wanted
            or str(ref.get('external_id')) in wanted or str(ref.get('raw_document_id')) in associated_raw)
    active=[]
    for c in claims:
        matching=[r for key,r in refs.items() if relevant(key,r) and r.get('claim_id')==str(c.get('id')) and r.get('claim_revision')==c.get('revision')]
        if not c.get('details',{}).get('superseded') and any(r.get('is_current') is True and r.get('stance')=='support' for r in matching):active.append(c)
    for a,b in combinations(active,2):
        kind=compare_claims({'type':a.get('claim_type'),'scope':a.get('scope_key'),'value':a.get('value_json',{})},
                            {'type':b.get('claim_type'),'scope':b.get('scope_key'),'value':b.get('value_json',{})})
        if kind:conflicts.append({'conflict_type':kind,'scope_key':a.get('scope_key'),'claim_a':a,'claim_b':b,'status':'unverified_conflict'})
    confirmed=any(c.get('trusted') is True and c.get('verification_status')=='CONFIRMED' and any(
        r.get('verified') is True and r.get('claim_id')==str(c.get('id')) and r.get('claim_revision')==c.get('revision')
        and r.get('stance')=='support' and r.get('is_current') is True for r in refs.values()) for c in active)
    for r in outcome.receipts:
        if r.envelope.status=='failed':failed.append({'tool':r.name,'call_index':r.call_index,'errors':_copy(r.envelope.errors)})
    partial=any(r.envelope.status in ('partial','failed','no_result') for r in outcome.receipts) or artifact.status in (TaskState.FAILED,TaskState.BLOCKED)
    values.update(failed_tools=failed,partial_result=partial,conflicts=conflicts)
    has_data=bool(details or values.get('asset') or findings)
    enough=bool(values.get('asset') and not targets) or (has_data and any(
        _credible(r) and relevant(key,r) for key,r in refs.items()))
    if conflicts:values.update(status='PARTIAL' if failed else 'CONFLICT',information_status='CONFLICT');values['uncertainties'].append('Current same-scope source assertions conflict; verification required')
    elif not enough:values.update(status='PARTIAL' if failed else 'INSUFFICIENT_EVIDENCE',information_status='INSUFFICIENT_EVIDENCE');values['uncertainties'].append('No sufficient current traceable authoritative source or target data')
    else:values.update(status='PARTIAL' if partial else 'COMPLETE',information_status='CONFIRMED' if confirmed else 'CANDIDATE')
    if failed:values['uncertainties'].extend('Tool failed: '+f['tool'] for f in failed)
    values['uncertainties']=list(dict.fromkeys(values['uncertainties']))
    # Reserve the Store's formal receipt IDs before accepting a complete projection.
    candidate=InvestigationArtifact.model_construct(**values)
    expanded=candidate.model_dump(mode='json')
    expanded['tool_calls']=[{**c,'record_id':c.get('record_id','ffffffff-ffff-ffff-ffff-ffffffffffff'),
        'sequence_no':c.get('sequence_no',32)} for c in values['tool_calls']]
    try:json_bytes(expanded,ARTIFACT_LIMIT)
    except ValueError as exc:
        # Only an actual size failure permits a bounded pointer, never invalid data.
        if 'size limit' not in str(exc):raise
        return InvestigationArtifact(artifact_id=artifact.artifact_id,run_id=artifact.run_id,task_id=artifact.task_id,
            runtime_status=artifact.status,status='PARTIAL',partial_result=True,confidence=artifact.confidence,
            information_status=values['information_status'],failed_tools=failed,
            tool_calls=artifact.tool_calls,dependency_artifact_ids=values['dependency_artifact_ids'],
            evidence_storage='tool_receipts',receipt_references=evidence_reference(outcome.receipts),
            uncertainties=['ARTIFACT_SIZE_LIMIT: full observations and evidence remain in tool receipts',
                'Information status retained: '+values['information_status']])
    return InvestigationArtifact(**values)
