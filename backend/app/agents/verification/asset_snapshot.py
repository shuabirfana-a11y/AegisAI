"""Project formal inventory receipts into a frozen version observation."""
from uuid import UUID,uuid5,NAMESPACE_URL
from packageurl import PackageURL
from app.agents.contracts import fingerprint
from app.agents.asset_observations import VersionObservation, InvestigationArtifactReference, ImpactVersionEvidence


def candidate_version_value(item,claim):
    value={k:item[k] for k in ('raw_expression','events','range_type','explicit_versions','parse_status','parse_reason') if k in item}
    # Package identity comes from the matching source Claim. Never infer an
    # ecosystem from the user's deployment or turn an unparsed range into a fact.
    value.update(ecosystem=claim.value.get('ecosystem') if claim else None,
                 package=claim.value.get('package') if claim else None)
    return value


def capture_version_observation(request,records,artifacts,claims,actor):
    if request.asset_id is None:return ()
    candidates=[]
    targets={c.package_identifier_id for c in claims if c.claim_type=='AFFECTS_VERSION' and c.package_identifier_id}
    for record,task_id in records:
        if record.tool_name!='get_asset':continue
        if str(record.input_summary.get('asset_id'))!=str(request.asset_id):raise ValueError('ASSET_RECEIPT_SCOPE_MISMATCH')
        envelope=record.output_summary
        if envelope.get('status')!='success':continue
        data=envelope.get('data') or {}
        if str(data.get('id'))!=str(request.asset_id) or data.get('owner_principal')!=actor:
            raise ValueError('ASSET_RECEIPT_OWNER_MISMATCH')
        rows=[c for c in data.get('components',[]) if not c.get('deleted_at')]
        if request.component_id:
            rows=[c for c in rows if str(c.get('id'))==str(request.component_id)]
        else:
            rows=[c for c in rows if str(c.get('package_identifier_id')) in targets]
        if len(rows)!=1:return ()
        c=rows[0]
        if str(c.get('asset_id'))!=str(request.asset_id):raise ValueError('COMPONENT_RECEIPT_SCOPE_MISMATCH')
        resolution=(c.get('details') or c.get('metadata') or {}).get('resolution') or {}
        package_name=resolution.get('package_name')
        if c.get('purl'):
            try:package_name=PackageURL.from_string(c['purl']).name
            except ValueError:pass
        art=artifacts[task_id]
        candidates.append(VersionObservation(id=uuid5(NAMESPACE_URL,str(record.id)+':'+str(c['id'])),
            asset_id=request.asset_id,component_id=c['id'],asset_name=data['name'],
            component=c.get('raw_package_name') or package_name or 'unknown',version=c.get('version'),
            package_identifier_id=str(c['package_identifier_id']) if c.get('package_identifier_id') else None,
            package_name=package_name,ecosystem=c.get('ecosystem') or 'unknown',namespace=c.get('namespace') or '',
            purl=c.get('purl'),environment=data.get('environment','unknown'),exposure=data.get('exposure','unknown'),
            inventory_revision=c['inventory_revision'],asset_updated_at=data['updated_at'],component_updated_at=c['updated_at'],
            created_at=record.finished_at,source_artifact=InvestigationArtifactReference(
                run_id=art.run_id,task_id=art.task_id,artifact_id=art.artifact_id),
            receipt_id=record.id,receipt_hash=fingerprint(record.output_summary),is_demo=data.get('is_demo',False)))
    if len(candidates)!=1:return ()
    return tuple(candidates)


def impact_references(claims,evidence):
    by_id={c.claim_id:c for c in claims if c.claim_type in ('AFFECTS_VERSION','FIXED_VERSION')}
    return tuple(ImpactVersionEvidence(id=e.evidence_id,vulnerability_id=e.vulnerability_id,
        package_identifier_id=by_id[e.claim_id].package_identifier_id,claim_id=e.claim_id,
        affected_versions=(by_id[e.claim_id].value,) if by_id[e.claim_id].claim_type=='AFFECTS_VERSION' else (),
        fixed_versions=(by_id[e.claim_id].value,) if by_id[e.claim_id].claim_type=='FIXED_VERSION' else (),
        evidence_ids=(e.evidence_id,),source=e.source_key,reference=e.reference,
        raw_document_id=e.raw_document_id,observation_id=e.observation_id,hash=e.hash)
        for e in evidence if e.claim_id in by_id)


def bind_impact_verdicts(references,claims):
    checked={c.claim.claim_id:c for c in claims}
    result=[]
    for ref in references:
        claim=checked.get(ref.claim_id)
        eligible=claim and ref.id in (*claim.supporting_evidence_ids,*claim.conflicting_evidence_ids)
        result.append(ref.model_copy(update={'status':claim.status if eligible else 'INSUFFICIENT_EVIDENCE'}))
    return tuple(result)


def validate_observation_handoff(assessment,snapshot):
    if assessment.partial_result and not (assessment.version_observations or assessment.impact_version_evidence):return
    if assessment.version_observations!=snapshot.version_observations:
        raise ValueError('VERSION_OBSERVATION_CHANGED')
    if assessment.impact_version_evidence!=bind_impact_verdicts(snapshot.impact_version_evidence,assessment.claims):
        raise ValueError('IMPACT_EVIDENCE_PROJECTION_CHANGED')
