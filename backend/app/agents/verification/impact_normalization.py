"""Source-bound canonical scope adapter before sealing, with original bindings."""
from copy import deepcopy
import json
from app.agents.contracts import fingerprint
from app.enrichment.versions import canonical_value,intervals
from app.enrichment.impact_scope import ImpactScope,ScopeEvidenceReference,scope_intervals,explicit_fixed_constraint,valid_fixed_version

KINDS={'AFFECTS_VERSION','FIXED_VERSION'}

def _witness(e,c):
    return (e.claim_id==c.claim_id and e.scope_key==c.scope_key and e.vulnerability_id==c.vulnerability_id
        and e.integrity_status=='VALID' and e.raw_document_id is not None and e.observation_id is not None
        and e.hash is not None and e.excerpt_hash is not None)

def _fixed(value,e):
    result=deepcopy(value)
    fixed=explicit_fixed_constraint(value,e.reference,e.content)
    if fixed is not None:result['version']=fixed
    return result

def normalize_bundle(claims,evidence,*,source_artifact_id=None,asset_id=None,coalesce=True):
    """Exact same semantic/scope facts may share proof; unequal claims cannot."""
    claims=tuple(claims);evidence=tuple(evidence);by_id={c.claim_id:c for c in claims}
    changed={};normalized_e=[]
    for c in claims:
        if c.claim_type not in KINDS:changed[c.claim_id]=c;continue
        value=deepcopy(c.value)
        if c.claim_type=='FIXED_VERSION' and value.get('version') is None:
            candidates={f for e in evidence if _witness(e,c) and e.stance=='support'
                and e.observed_value==c.value and (f:=explicit_fixed_constraint(value,e.reference,e.content)) is not None}
            if len(candidates)==1:value['version']=candidates.pop()
        updates={'value':value}
        if value!=c.value:updates['statement']=c.claim_type+' '+json.dumps(value,ensure_ascii=False)[:2100]
        changed[c.claim_id]=c.model_copy(update=updates)
    for e in evidence:
        c=by_id.get(e.claim_id);value=deepcopy(e.observed_value)
        if c and c.claim_type=='FIXED_VERSION' and _witness(e,c):value=_fixed(value,e)
        details=deepcopy(e.details)
        if c and c.claim_type in KINDS:
            details.update(source_claim_id=e.claim_id,original_observed_value=deepcopy(e.observed_value),
                normalization_version='impact-scope-v1')
            if any(c.value.get(k) for k in ('condition','platform','architecture')):
                e=e.model_copy(update={'exclusion_reasons':tuple(dict.fromkeys((*e.exclusion_reasons,'IMPACT_APPLICABILITY_UNRESOLVED')))})
            if c.claim_type=='AFFECTS_VERSION' and intervals(c.value) is not None and not scope_intervals(c.value):
                e=e.model_copy(update={'exclusion_reasons':tuple(dict.fromkeys((*e.exclusion_reasons,'IMPACT_SCOPE_LIMIT')))})
            if c.claim_type=='FIXED_VERSION' and changed[c.claim_id].value.get('version') is not None and not valid_fixed_version(changed[c.claim_id].value['version']):
                e=e.model_copy(update={'exclusion_reasons':tuple(dict.fromkeys((*e.exclusion_reasons,'UNSUPPORTED_FIXED_VERSION')))})
        normalized_e.append(e.model_copy(update={'observed_value':value,'details':details}))
    groups={}
    for c in changed.values():
        supported=bool(scope_intervals(c.value)) if c.claim_type=='AFFECTS_VERSION' else valid_fixed_version(c.value.get('version'))
        # No identity, unsupported input or explicitly selected raw IDs are not collapsed.
        collapse=coalesce and c.claim_type in KINDS and supported and c.package_identifier_id is not None
        semantic_meta={k:c.related_entities.get(k) for k in ('cvss_version','assessment_kind')}
        semantic_meta['superseded']=c.related_entities.get('superseded') is True
        semantic_meta['applicability']={k:c.value.get(k) for k in ('product','condition','platform','architecture')}
        key=fingerprint([c.vulnerability_id,c.claim_type,c.scope_key,c.package_identifier_id,c.branch,
            semantic_meta,canonical_value(c.claim_type,c.value)]) if collapse else 'unmerged:'+c.claim_id
        groups.setdefault(key,[]).append(c)
    out=[];aliases={}
    for group in groups.values():
        group=sorted(group,key=lambda c:c.claim_id);representative=group[0];ids=tuple(c.claim_id for c in group)
        for identifier in ids:aliases[identifier]=representative.claim_id
        local=[e for e in normalized_e if e.claim_id in ids]
        if representative.claim_type not in KINDS:out.append(representative);continue
        value=representative.value
        refs=tuple(ScopeEvidenceReference(evidence_id=e.evidence_id,source_claim_id=e.details['source_claim_id'],
            source_id=e.source_id,raw_document_id=e.raw_document_id,observation_id=e.observation_id,
            reference=deepcopy(e.reference)) for e in local)
        ranges=scope_intervals(value) if representative.claim_type=='AFFECTS_VERSION' else ()
        supported=bool(ranges) if representative.claim_type=='AFFECTS_VERSION' else valid_fixed_version(value.get('version'))
        scope=ImpactScope(vulnerability_id=representative.vulnerability_id,
            affected_product=value.get('product') if isinstance(value.get('product'),str) else None,
            affected_component=value.get('package') if isinstance(value.get('package'),str) else None,
            ecosystem=value.get('ecosystem'),affected_version_range=ranges,
            fixed_version=value.get('version') if representative.claim_type=='FIXED_VERSION' and supported else None,
            **{k:value.get(k) if isinstance(value.get(k),str) else None for k in ('condition','platform','architecture')},
            branch=representative.branch,source_artifact_id=source_artifact_id,asset_id=asset_id,
            source_claim_ids=ids,evidence_refs=refs,source_refs=tuple(sorted({str(e.source_id) for e in local if e.source_id})),
            normalization_state='NORMALIZED' if supported else 'UNSUPPORTED')
        out.append(representative.model_copy(update={'impact_scope':scope,'evidence_ids':tuple(e.evidence_id for e in local)}))
    rebound=tuple(e.model_copy(update={'claim_id':aliases[e.claim_id]}) if e.claim_id in aliases else e for e in normalized_e)
    return tuple(sorted(out,key=lambda c:c.claim_id)),rebound
