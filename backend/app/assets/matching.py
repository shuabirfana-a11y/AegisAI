"""Package-scoped deterministic match, followed by the existing intelligence trust gate."""
from sqlalchemy import select
from app.db import models as m
from app.enrichment.evidence import current_evidence,EvidenceService
from app.enrichment.repository import ClaimStore,digest
from app.assets.versions import compare_version
from app.services.versions import parse_expression
from app.utils.time import utcnow
from datetime import timedelta
from app.enrichment.versions import intervals,merge_intervals
from app.assets.remediation import trusted_claim

MATCHER='asset-pypi-v1'

def _range_value(r,ecosystem):
    return {'ecosystem':ecosystem,'range_type':r.range_type,'raw_expression':r.raw_expression,'events':r.events,
        'explicit_versions':r.explicit_versions,'parse_status':r.parse_status}

def _current_ranges(session,package_id,vuln):
    rows=list(session.scalars(select(m.AffectedVersionRange).where(m.AffectedVersionRange.package_identifier_id==package_id,m.AffectedVersionRange.vulnerability_id==vuln)))
    result=[]
    for r in rows:
        o=session.get(m.SourceObservation,r.observation_id)
        latest=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==r.source_id,m.SourceObservation.external_id==o.external_id,
            m.SourceObservation.parse_status=='parsed').order_by(m.SourceObservation.retrieved_at.desc(),m.SourceObservation.created_at.desc(),m.SourceObservation.id.desc()).limit(1))
        if latest==o.id:result.append(r)
    return result

def _assertions(session,component,vuln,ranges):
    pkg=session.get(m.PackageIdentifier,component.package_identifier_id)
    claims=list(session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==vuln,m.Claim.claim_type.in_(['AFFECTS_VERSION','affected_version']),
        m.Claim.package_identifier_id==pkg.id)))
    claims=[c for c in claims if not c.details.get('superseded') and any(e['is_current'] and e['stance']=='support' for e in current_evidence(session,c))]
    covered={session.get(m.Evidence,e['id']).observation_id for c in claims for e in current_evidence(session,c) if e['is_current'] and e['stance']=='support'}
    all_by_obs={}
    for r in ranges:all_by_obs.setdefault(r.observation_id,[]).append(r)
    for obs_id in list(covered):
        source_union=[];supported=True
        for r in all_by_obs.get(obs_id,[]):
            value=intervals(_range_value(r,pkg.ecosystem))
            if value is None:supported=False;break
            source_union.extend(value)
        # Only whole-source unions count as covering an observation's ranges.
        group=[c for c in claims if any(session.get(m.Evidence,e['id']).observation_id==obs_id for e in current_evidence(session,c) if e['is_current'] and e['stance']=='support')]
        if all_by_obs.get(obs_id) and (not supported or not any(intervals(c.value_json)==merge_intervals(source_union) for c in group)):covered.discard(obs_id)
    # Bridge existing Phase6 assertions to evidence without declaring new verified facts.
    by_obs={}
    for r in ranges:
        if r.observation_id not in covered:by_obs.setdefault(r.observation_id,[]).append(r)
    for obs_id,parts in by_obs.items():
        value={'ecosystem':pkg.ecosystem,'package':pkg.package_name,'ranges':[_range_value(r,pkg.ecosystem) for r in parts]}
        c=ClaimStore.add(session,vuln,'AFFECTS_VERSION',pkg.ecosystem+':'+pkg.package_name,value,subject={'package_identifier_id':pkg.id},details={'phase8_source_assertion':True})
        o=session.get(m.SourceObservation,obs_id)
        for r in parts:EvidenceService.add(session,c,o,value,{'range_id':str(r.id)},evidence_type='normalized_version')
        if c.id not in {x.id for x in claims}:claims.append(c)
    return claims

def _ranges_for_claim(session,claim,ranges,package):
    evidence=[session.get(m.Evidence,e['id']) for e in current_evidence(session,claim) if e['is_current'] and e['stance']=='support']
    obs_ids={e.observation_id for e in evidence};found=[r for r in ranges if r.observation_id in obs_ids]
    # Phase7 vendor assertions are trustworthy objects but did not need a persisted range row.
    if not found and claim.value_json.get('range') and evidence:
        parsed=parse_expression(claim.value_json['range'],package.ecosystem)
        if parsed['parse_status']=='parsed':
            e=evidence[0]
            row=m.AffectedVersionRange(vulnerability_id=claim.vulnerability_id,product_id=package.product_id,package_identifier_id=package.id,
                source_id=e.source_id,observation_id=e.observation_id,scope_key=claim.scope_key,range_type='ECOSYSTEM',raw_expression=claim.value_json['range'],
                introduced=parsed['introduced'],fixed=parsed['fixed'],last_affected=parsed['last_affected'],explicit_versions=parsed['explicit_versions'],
                # Retain expression conjunction semantics instead of token-order event semantics.
                parse_status='parsed',parser_version='phase8-vendor-range-v1',verification_status=claim.verification_status,
                details={'derived_from_claim_id':str(claim.id),'evidence_id':str(e.id)})
            session.add(row);session.flush();found=[row]
    return found,evidence

class AssetVulnerabilityMatcher:
    @staticmethod
    def match(session,component):
        if component.deleted_at or component.package_identifier_id is None:return []
        package=session.get(m.PackageIdentifier,component.package_identifier_id)
        # Exact distribution only; product relation is not itself an alert.
        candidates=set(session.scalars(select(m.AffectedVersionRange.vulnerability_id).where(m.AffectedVersionRange.package_identifier_id==package.id)))
        candidates.update(session.scalars(select(m.Claim.vulnerability_id).where(m.Claim.package_identifier_id==package.id,m.Claim.claim_type=='AFFECTS_VERSION')))
        results=[]
        for vid in sorted(candidates,key=str):
            vuln=session.get(m.Vulnerability,vid)
            if vuln is None or vuln.deleted_at:continue
            ranges=_current_ranges(session,package.id,vid);claims=_assertions(session,component,vid,ranges)
            evaluations=[];evidence=[];range_rows=[]
            for c in claims:
                found,ev=_ranges_for_claim(session,c,ranges,package);range_rows.extend(found);evidence.extend(ev)
                comparison=compare_version(component.version,c.value_json)
                evaluations.append({'claim_id':str(c.id),'revision':c.revision,'status':c.verification_status,'adopted':c.adopted,'value':c.value_json,**comparison})
            definite=[x['affected'] for x in evaluations]
            technical='AFFECTED' if definite and all(v is True for v in definite) else 'NOT_AFFECTED' if definite and all(v is False for v in definite) else 'UNCERTAIN'
            now=utcnow()
            trusted=bool(claims) and all(trusted_claim(session,c,now=now) for c in claims)
            conflicts=list(session.scalars(select(m.ConflictRecord).where(m.ConflictRecord.vulnerability_id==vid,m.ConflictRecord.status=='open',m.ConflictRecord.scope_key==package.ecosystem+':'+package.package_name)))
            status=technical if trusted and not conflicts else 'UNCERTAIN'
            verification='CONFLICT' if conflicts or any(x['status']=='conflict' for x in evaluations) else 'CONFIRMED' if trusted else 'INSUFFICIENT_EVIDENCE'
            if vuln.status!='published':status='NOT_EVALUATED'
            if status in ('AFFECTED','NOT_AFFECTED') and not range_rows:status='UNCERTAIN'
            reason='All current exact-package ranges and adopted verified claims agree' if status in ('AFFECTED','NOT_AFFECTED') else 'Unsupported/missing version, unverified assertion or unresolved range conflict; no definite safety conclusion'
            if status=='NOT_EVALUATED':reason='Vulnerability is withdrawn/rejected/unknown; retained for history'
            refs=[{'evidence_id':str(e.id),'claim_id':str(e.claim_id),'source_id':str(e.source_id),'source_key':session.get(m.Source,e.source_id).source_key,
                'observation_id':str(e.observation_id),'raw_document_id':str(e.raw_document_id),'source_url':e.source_url,'locator':e.locator} for e in evidence]
            ranges_out=[{'range_id':str(r.id),'raw_expression':r.raw_expression,'source_id':str(r.source_id),'observation_id':str(r.observation_id),'parse_status':r.parse_status} for r in range_rows]
            signature=digest([component.version,component.inventory_revision,[(str(c.id),c.revision,c.verification_status,c.adopted) for c in claims],
                sorted(e['fingerprint'] for c in claims for e in current_evidence(session,c) if e['is_current']),sorted(str(c.id) for c in conflicts),vuln.status,status,verification,technical])
            result={'component_id':str(component.id),'vulnerability_id':str(vid),'canonical_id':vuln.canonical_id,'installed_version':component.version,'package_identifier_id':str(package.id),
                'match_status':status,'version_result':technical,'verification_status':verification,'reason_summary':reason,'component_revision':component.inventory_revision,
                'claim_ids':[str(c.id) for c in claims],'claim_revisions':{str(c.id):c.revision for c in claims},'affected_ranges':ranges_out,
                'comparisons':[comparison for x in evaluations for comparison in x['comparisons']],
                'source_evaluations':evaluations,'evidence_refs':refs,'conflict_ids':[str(c.id) for c in conflicts],'fingerprint':signature}
            results.append(result)
        return results
