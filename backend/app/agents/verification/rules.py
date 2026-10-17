"""Pure snapshot adapter to the existing, deterministic trust kernels."""
from datetime import timedelta
from itertools import combinations
from app.agents.contracts import fingerprint
from app.enrichment.rules import evaluate_claim, compare_claims
from app.enrichment.contracts import VerificationStatus as Status
from app.enrichment.version_scope import evidence_scopes,compare_scopes
from app.agents.verification.snapshot import authority_weight, scope_supported
from app.agents.verification.schemas import (
    VerificationContext,VerificationAssessment,ClaimVerification,VerificationConflict,
)


def _scope(claim):
    return fingerprint([claim.vulnerability_id,claim.scope_key,claim.package_identifier_id,claim.branch,
        claim.related_entities.get('cvss_version') or (claim.value.get('version') if claim.claim_type=='CVSS_SCORE' else None),
        claim.related_entities.get('assessment_kind')])


def _eligible(item,claim,now):
    reasons=list(item.exclusion_reasons)
    if item.claim_id!=claim.claim_id or item.scope_key!=claim.scope_key or item.vulnerability_id!=claim.vulnerability_id:
        reasons.append('UNRELATED_CLAIM_OR_SCOPE')
    for key in ('ecosystem','package'):
        if claim.value.get(key) and item.observed_value.get(key)!=claim.value[key]:
            reasons.append('PACKAGE_IDENTITY_MISMATCH')
    if item.integrity_status!='VALID' or not item.hash or not item.excerpt_hash or not item.raw_document_id or not item.observation_id:
        reasons.append('INCOMPLETE_OR_INVALID_PROVENANCE')
    if not item.content or not item.reference.get('url'):reasons.append('MISSING_QUOTE_OR_REFERENCE')
    if not scope_supported(item.authority_scope,claim,source_key=item.source_key,reference=item.reference) or item.authority_level is None:
        reasons.append('SOURCE_AUTHORITY_UNRESOLVED')
    if not item.is_current:reasons.append('NONCURRENT_SOURCE')
    if item.retrieved_at is None or item.retrieved_at<now-timedelta(days=30) or item.retrieved_at>now+timedelta(minutes=5):
        reasons.append('EVIDENCE_TIME_OUTSIDE_WINDOW')
    if item.published_at and (item.published_at>now+timedelta(minutes=5) or
        item.retrieved_at and item.published_at>item.retrieved_at+timedelta(minutes=5)):
        reasons.append('SOURCE_TIME_INCONSISTENT')
    if claim.related_entities.get('superseded'):reasons.append('SUPERSEDED_CLAIM')
    return tuple(dict.fromkeys(reasons))


def _wire(item):
    return {'id':item.evidence_id,'lineage':item.lineage_key or 'unresolved-origin','authority':item.authority_level,
        'value':item.observed_value,'stance':item.stance,'retrieved_at':item.retrieved_at,
        'explicit':item.directness=='direct' and item.details.get('explicit') is True,
        'is_current':item.is_current,'evidence_type':item.evidence_type,'details':item.details}


def _scan_conflicts(claims,evidence,selected=()):
    by_id={c.claim_id:c for c in claims}
    scopes={c.claim_id:_scope(c) for c in claims}
    entries=[(by_id[e.claim_id],e) for e in evidence if e.claim_id in by_id and e.stance=='support'
        and e.directness=='direct' and e.details.get('explicit') is True]
    conflicts=[];seen=set();affected={};overflow=False;selected=set(selected)
    for (a,ea),(b,eb) in combinations(entries,2):
        if selected and not {a.claim_id,b.claim_id}&selected:continue
        if ea.evidence_id==eb.evidence_id or scopes[a.claim_id]!=scopes[b.claim_id]:continue
        # Use observed source values, including two different values bound to one Claim.
        scope=scopes[a.claim_id]
        kind=compare_claims({'scope':scope,'type':a.claim_type,'value':ea.observed_value,'version_scopes':evidence_scopes(ea,a.claim_type)},
                            {'scope':scope,'type':b.claim_type,'value':eb.observed_value,'version_scopes':evidence_scopes(eb,b.claim_type)})
        if not kind:continue
        claim_ids=tuple(sorted({a.claim_id,b.claim_id}));evidence_ids=tuple(sorted({ea.evidence_id,eb.evidence_id}))
        for identifier in claim_ids:affected.setdefault(identifier,set()).update(evidence_ids)
        key=(kind,claim_ids,evidence_ids)
        if key in seen:continue
        seen.add(key)
        if len(conflicts)>=128:
            overflow=True;continue
        conflict=VerificationConflict(conflict_type=kind,claim_ids=claim_ids,
            evidence_ids=evidence_ids,scope_key=a.scope_key,
            reason='Current direct sources disagree within the same vulnerability/package/branch scope')
        conflicts.append(conflict)
    return tuple(conflicts),overflow,affected


def find_conflicts(claims,evidence):
    return _scan_conflicts(claims,evidence)[0]


def _quality(evidence):
    groups={};components=[]
    for item in evidence:
        source=authority_weight(item.authority_level,item.source_type)
        direct=1.0 if item.directness=='direct' and item.details.get('explicit') is True else 0.25 if item.directness=='mention' else 0
        score=source*direct
        lineage=item.lineage_key or 'unresolved-origin'
        groups[lineage]=max(score,groups.get(lineage,0))
        components.append({'evidence_id':item.evidence_id,'source_weight':source,'directness_weight':direct,
                           'quality':score,'lineage':lineage})
    ordered=sorted(groups.values(),reverse=True)
    score=(ordered[0] if ordered else 0)+(0.1*ordered[1] if len(ordered)>1 else 0)
    return round(min(1,score),6),components


def evaluate_snapshot(context,*,claim_ids=()):
    context=VerificationContext.model_validate_json(context.model_dump_json())
    claims=context.snapshot.claims
    selected=claim_ids or context.request.claim_ids or tuple(c.claim_id for c in claims)
    if set(selected)-{c.claim_id for c in claims}:raise ValueError('Selected claim is not in the sealed source snapshot')
    usable=[];excluded={};by_claim={c.claim_id:c for c in claims}
    for item in context.snapshot.evidence:
        c=by_claim.get(item.claim_id)
        if c is None:continue
        bad=_eligible(item,c,context.evaluation_time)
        if bad:excluded.setdefault(c.claim_id,[]).append({'evidence_id':item.evidence_id,'reasons':list(bad)})
        else:usable.append(item)
    # Historical derived counter-evidence stays in the sealed snapshot. Its
    # applicability is checked against valid supporting source-entry witnesses.
    retained=[]
    for item in usable:
        c=by_claim[item.claim_id]
        if item.stance=='contradict' and item.details.get('conflict_id') and c.claim_type in ('AFFECTS_VERSION','FIXED_VERSION'):
            support_scopes=[scope for e in usable if e.claim_id==c.claim_id and e.stance=='support'
                            for scope in evidence_scopes(e,c.claim_type)]
            comparison=compare_scopes({'type':c.claim_type,'value':c.value,'version_scopes':support_scopes},
                {'type':c.claim_type,'value':item.observed_value,'version_scopes':evidence_scopes(item,c.claim_type)})
            if comparison.result in ('DIFFERENT_SCOPE','BRANCH_DIFFERENCE'):
                excluded.setdefault(c.claim_id,[]).append({'evidence_id':item.evidence_id,
                    'reasons':['PROVEN_DIFFERENT_VERSION_SCOPE'],'comparison':comparison.model_dump(mode='json')})
                continue
        retained.append(item)
    usable=retained
    conflicts,conflicts_omitted,conflict_map=_scan_conflicts(claims,tuple(usable),selected)
    results=[];warnings=list(context.snapshot.warnings);support_ids=set();conflict_ids=set()
    if conflicts_omitted:warnings.append('CONFLICT_LIMIT_REACHED: detailed relationships capped at 128; all bounded source pairs were checked')
    unresolved=list(context.snapshot.unresolved_items)
    for c in claims:
        if c.claim_id not in selected:continue
        local=[e for e in usable if e.claim_id==c.claim_id]
        decision=evaluate_claim(c.claim_type,c.value,[_wire(e) for e in local],context.evaluation_time)
        status=Status(decision['status'])
        supports=set(decision['supporting_evidence']);counters=set(decision['contradicting_evidence'])
        related=conflict_map.get(c.claim_id,set())
        if related:
            status=Status.CONFLICT
            counters.update(related)
        if context.request.task_type=='conflict_detection' and status!=Status.CONFLICT:status=Status.PENDING
        score,parts=_quality([e for e in local if e.evidence_id in supports])
        counter_score,counter_parts=_quality([e for e in usable if e.evidence_id in counters])
        if status==Status.REJECTED:score=0
        elif status!=Status.CONFIRMED:score=min(0.49,score)
        cwarnings=['Excluded '+x['evidence_id']+': '+','.join(x['reasons']) for x in excluded.get(c.claim_id,[])]
        if c.claim_type in ('POC_ASSOCIATION','POC_EXISTS'):
            warnings.append('POC_NOT_EXECUTED: static association does not establish usability')
        problem=() if status==Status.CONFIRMED else (decision['reason_summary'] if not related else 'Conflicting current source values',)
        result=ClaimVerification(claim=c.model_copy(update={'status':status}),status=status,confidence=score,
            supporting_evidence_ids=tuple(sorted(supports)),conflicting_evidence_ids=tuple(sorted(counters)),
            reason_code='SOURCE_CONFLICT' if related else decision['method'],reason_summary=problem[0] if problem else decision['reason_summary'],
            rules_applied=('identity','provenance','source_scope','directness','currentness','time','independence','deterministic-evidence-v1'),
            score_components={'support':parts,'support_score':score,'counter':counter_parts,'counter_score':counter_score,
                              'excluded':excluded.get(c.claim_id,[])},warnings=tuple(cwarnings),unresolved_items=problem)
        results.append(result);support_ids.update(supports);conflict_ids.update(counters)
        unresolved.extend(problem)
    partial=bool(conflicts_omitted or context.snapshot.omitted_claim_count or context.snapshot.omitted_evidence_count or
                 context.snapshot.artifact.get('status')=='PARTIAL')
    states=[r.status for r in results]
    if any(s==Status.CONFLICT for s in states):status=Status.CONFLICT
    elif states and all(s==Status.CONFIRMED for s in states) and not partial:status=Status.CONFIRMED
    elif states and all(s==Status.REJECTED for s in states) and not partial:status=Status.REJECTED
    elif support_ids or any(s==Status.PENDING for s in states):status=Status.PENDING
    else:status=Status.INSUFFICIENT_EVIDENCE
    if partial:unresolved.append('PARTIAL_INPUT: not all observations/claims/evidence were processed')
    confidence=min((r.confidence for r in results),default=0)
    if status not in (Status.CONFIRMED,Status.REJECTED):confidence=min(0.49,confidence)
    return VerificationAssessment(claims=tuple(results),verification_status=status,confidence=confidence,
        supporting_evidence=tuple(e for e in usable if e.evidence_id in support_ids),
        conflicting_evidence=tuple(e for e in usable if e.evidence_id in conflict_ids),conflicts=conflicts,
        warnings=tuple(dict.fromkeys(warnings)),unresolved_items=tuple(dict.fromkeys(unresolved)),partial_result=partial)
