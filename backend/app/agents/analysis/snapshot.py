"""Read exact owner-bound prior results and inventory, without discovery or reverification."""
from uuid import UUID
from sqlalchemy import select
from packageurl import PackageURL
from app.db import models as m
from app.db.session import transaction
from app.agents.contracts import AgentFrameworkError, fingerprint
from app.agents.investigation.reader import InvestigationReader
from app.agents.verification.reader import VerificationReader
from app.agents.verification.context_store import VerificationContextStore
from app.assets.inventory import owned_asset
from app.assets.identity import resolve_component
from app.agents.analysis.schemas import AnalysisRequest,AnalysisInputs,AssetContextSnapshot


class AnalysisSnapshotReader:
    def __init__(self,engine):self.engine=engine

    def _asset(self,db,request,claims,actor,now):
        if request.asset_id is None:
            return AssetContextSnapshot(captured_at=now,unresolved_items=('ASSET_CONTEXT_MISSING',))
        asset=owned_asset(db,request.asset_id,actor)
        base=dict(asset_id=asset.id,captured_at=now,asset_updated_at=asset.updated_at,
                  environment=asset.environment,exposure=asset.exposure,is_demo=asset.is_demo)
        rows=list(db.scalars(select(m.AssetComponent).where(m.AssetComponent.asset_id==asset.id,
            m.AssetComponent.deleted_at.is_(None)).order_by(m.AssetComponent.id).limit(101)))
        if request.component_id:
            component=db.get(m.AssetComponent,request.component_id)
            if component is None or component.asset_id!=asset.id or component.deleted_at:
                raise LookupError('Asset not found')
        else:
            if len(rows)>100:
                return AssetContextSnapshot(**base,context_status='LIMITED',unresolved_items=('INVENTORY_LIMIT',))
            targets={c.package_identifier_id for c in claims if c.claim_type=='AFFECTS_VERSION' and c.package_identifier_id}
            selected=[c for c in rows if str(c.package_identifier_id) in targets]
            if len(selected)!=1:
                return AssetContextSnapshot(**base,context_status='AMBIGUOUS' if len(selected)>1 else 'UNRESOLVED',
                    unresolved_items=('SELECT_EXACT_COMPONENT',))
            component=selected[0]
        package=db.get(m.PackageIdentifier,component.package_identifier_id) if component.package_identifier_id else None
        resolved=None
        try:
            if component.purl:
                purl=PackageURL.from_string(component.purl)
                if purl.qualifiers or purl.subpath:raise ValueError('Qualified identity needs explicit applicability')
            resolved=resolve_component(db,{'name':component.raw_package_name or 'unknown',
                'package_identifier_id':component.package_identifier_id,'package_name':package.package_name if package else None,
                'ecosystem':package.ecosystem if package else component.ecosystem,
                'namespace':package.namespace if package else component.namespace or '',
                'purl':component.purl,'version':component.version})
        except (ValueError,TypeError):pass
        valid=bool(resolved and resolved['status']=='RESOLVED')
        return AssetContextSnapshot(**base,component_id=component.id,component=component.raw_package_name,
            package_identifier_id=str(resolved['package_identifier_id']) if valid else None,
            package_name=resolved['package_name'] if valid else None,
            ecosystem=resolved['ecosystem'] if valid else component.ecosystem or 'unknown',
            namespace=resolved.get('namespace','') if valid else component.namespace or '',purl=component.purl,
            deployed_version=component.version,inventory_revision=component.inventory_revision,
            component_updated_at=component.updated_at,context_status='RESOLVED' if valid else 'UNRESOLVED',
            unresolved_items=() if valid else ('COMPONENT_IDENTITY_UNRESOLVED',))

    def read(self,request,*,actor,evaluation_time):
        request=AnalysisRequest.model_validate_json(request.model_dump_json())
        try:
            found=InvestigationReader(self.engine).read(request.investigation_run_id,actor)
            investigation=next(a for a in found.artifacts if a.task_id==request.investigation_task_id
                               and a.artifact_id==request.investigation_artifact_id)
            found=VerificationReader(self.engine).read(request.verification_run_id,actor=actor)
            verification=next(a for a in found.artifacts if a.task_id==request.verification_task_id
                              and a.artifact_id==request.verification_artifact_id)
            with transaction(self.engine) as db:
                run=db.get(m.AgentRun,request.verification_run_id)
                route=run.details['runtime_v1']['plan']['route']['verification_v1']
                sealed=VerificationContextStore(self.engine).read(route['context_id'],actor=actor)
                source=sealed.snapshot
                if ((source.source_run_id,source.source_task_id,source.source_artifact_id)!=
                    (investigation.run_id,investigation.task_id,investigation.artifact_id) or
                    verification.source_snapshot_hash!=sealed.source_snapshot_hash or
                    fingerprint(source.artifact)!=fingerprint(investigation.model_dump(mode='json'))):
                    raise ValueError('Source identity/hash mismatch')
                source_claims={c.claim_id:c for c in source.claims}
                evidence={e.evidence_id:e for e in source.evidence}
                for checked in verification.claims:
                    original=source_claims.get(checked.claim.claim_id)
                    if original is None or (fingerprint(original.model_dump(mode='json',exclude={'status'}))!=
                        fingerprint(checked.claim.model_dump(mode='json',exclude={'status'}))):
                        raise ValueError('Claim differs from fixed verification input')
                    if checked.claim.status!=checked.status:raise ValueError('Claim result status mismatch')
                    for eid in checked.supporting_evidence_ids:
                        if eid not in evidence or evidence[eid].claim_id!=original.claim_id:
                            raise ValueError('Evidence differs from fixed verification input')
                    for eid in checked.conflicting_evidence_ids:
                        if eid not in evidence:raise ValueError('Unknown counter-evidence')
                        other=source_claims.get(evidence[eid].claim_id)
                        if other is None:raise ValueError('Unknown counter-claim')
                        if other.claim_id!=original.claim_id:
                            from app.agents.verification.rules import _scope
                            if _scope(other)!=_scope(original) or not any(
                                {original.claim_id,other.claim_id}<=set(conflict.claim_ids) and
                                eid in conflict.evidence_ids and conflict.scope_key==original.scope_key
                                for conflict in verification.conflicts):
                                raise ValueError('Counter-evidence has no fixed conflict relationship')
                for item in (*verification.supporting_evidence,*verification.conflicting_evidence):
                    fixed=evidence.get(item.evidence_id)
                    if fixed is None or fingerprint(item.model_dump(mode='json'))!=fingerprint(fixed.model_dump(mode='json')):
                        raise ValueError('Evidence projection differs from fixed input')
                refs=[];epss=[]
                for ref in source.receipt_references:
                    record=db.get(m.ToolCallRecord,UUID(ref['record_id']))
                    if (record is None or record.agent_run_id!=investigation.run_id or
                        record.tool_name!=ref['tool_name'] or record.sequence_no!=ref['sequence_no'] or
                        fingerprint(record.input_summary)!=ref['input_hash'] or
                        fingerprint(record.output_summary)!=ref['output_hash']):
                        raise ValueError('Input receipt changed')
                    refs.append(dict(ref))
                    data=record.output_summary.get('data') or {}
                    if isinstance(data,dict):
                        intel=data.get('intelligence') or {}
                        rows=intel.get('epss',[]) if isinstance(intel,dict) else []
                        if isinstance(rows,dict):rows=rows.get('items',[])
                        if record.tool_name=='get_epss':rows=data.get('items',[])
                        for item in rows[:10-len(epss)]:
                            epss.append({**item,'receipt_id':ref['record_id'],'provenance':'SOURCE_ASSERTED'})
        except (ValueError,TypeError,KeyError,LookupError,StopIteration,AttributeError):
            raise AgentFrameworkError('INVALID_INPUT_ARTIFACT') from None
        with transaction(self.engine) as db:
            asset=self._asset(db,request,source.claims,actor,evaluation_time)
        values=dict(investigation=investigation,verification=verification,asset=asset,
            source_claims=source.claims,source_verification_task=sealed.request.task_type,
            source_snapshot_hash=sealed.source_snapshot_hash,receipt_references=tuple(refs),
            omitted_claim_count=source.omitted_claim_count,omitted_evidence_count=source.omitted_evidence_count,
            coverage_complete=not (source.omitted_claim_count or source.omitted_evidence_count),epss=tuple(epss))
        try:return AnalysisInputs(**values)
        except ValueError as error:
            if 'size limit' not in str(error):raise AgentFrameworkError('INVALID_INPUT_ARTIFACT') from None
            values.update(source_claims=(),receipt_references=(),epss=(),coverage_complete=False,
                          warnings=('ANALYSIS_INPUT_LIMIT: source inputs remain in original sealed context',))
            return AnalysisInputs(**values)
