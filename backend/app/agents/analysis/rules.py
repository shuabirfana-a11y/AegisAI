"""Consume verification decisions; reuse existing comparators and published priority policy."""
import math
from datetime import date,timedelta
from app.assets.versions import compare_version
from app.assets.priority import assess_priority
from app.agents.contracts import fingerprint
from app.agents.analysis.schemas import (AnalysisContext,AssetMatchResult,VersionMatchResult,RiskAssessment,
    RiskFactor,ExploitationSignal,PatchAvailability)


def value_matches_distribution(value,asset,*,required=False):
    from app.assets.identity import _name
    if required and (not asset.package_name or not value.get('ecosystem') or not value.get('package')):return False
    if value.get('ecosystem') and value['ecosystem']!=asset.ecosystem:return False
    if value.get('package') and (not isinstance(value['package'],str) or not asset.package_name or
        _name(value['package'],asset.ecosystem)!=_name(asset.package_name,asset.ecosystem)):return False
    return value.get('namespace',asset.namespace)==asset.namespace


def claim_applies_to_distribution(claim,asset,*,require_identity=False):
    if claim.branch or claim.value.get('branch'):return False
    if claim.package_identifier_id and claim.package_identifier_id!=asset.package_identifier_id:return False
    if require_identity and claim.package_identifier_id!=asset.package_identifier_id:return False
    return value_matches_distribution(claim.value,asset,required=require_identity)


def confirmed_claims(context):
    """Identity/citation binding is a consumption check, never a new evidence verdict."""
    inputs=context.inputs;root=inputs.investigation.vulnerability_id
    original={c.claim_id:c for c in inputs.source_claims}
    refs={e.evidence_id:e for e in inputs.verification.supporting_evidence}
    result=[]
    for checked in inputs.verification.claims:
        c=checked.claim;old=original.get(c.claim_id)
        if checked.status!='CONFIRMED' or c.status!=checked.status or c.vulnerability_id!=root or old is None:continue
        if fingerprint(c.model_dump(mode='json',exclude={'status'}))!=fingerprint(old.model_dump(mode='json',exclude={'status'})):continue
        if not checked.supporting_evidence_ids or not all(e in refs and refs[e].claim_id==c.claim_id for e in checked.supporting_evidence_ids):continue
        result.append(checked)
    return tuple(result)


def match_asset(context):
    asset=context.inputs.asset
    if asset.context_status!='RESOLVED' or not asset.package_identifier_id:
        return AssetMatchResult(reason='Asset identity/context is missing or ambiguous')
    claims=[r.claim for r in confirmed_claims(context) if r.claim.claim_type=='AFFECTS_VERSION' and r.claim.package_identifier_id]
    if not claims:return AssetMatchResult(reason='No confirmed exact-package impact claim')
    matches=[c for c in claims if c.package_identifier_id==asset.package_identifier_id]
    return AssetMatchResult(status='MATCHED' if matches else 'NOT_MATCHED',
        reason='Exact distribution identity matches' if matches else 'Only the selected component differs from the confirmed target distribution',
        claim_ids=tuple(c.claim_id for c in matches or claims),package_identifier_id=asset.package_identifier_id)


def match_version(context,asset_match):
    if asset_match.status!='MATCHED':return VersionMatchResult(reason='No exact matching asset component')
    asset=context.inputs.asset
    results=[r for r in confirmed_claims(context) if r.claim.claim_id in asset_match.claim_ids]
    if any(not value_matches_distribution(r.claim.value,asset,required=True) for r in results):
        return VersionMatchResult(reason='Range distribution identity differs from resolved inventory')
    if not results or any(r.claim.branch or r.claim.value.get('branch') for r in results):
        return VersionMatchResult(reason='Branch-specific applicability is unresolved')
    values=[(r.claim.claim_id,compare_version(asset.deployed_version,r.claim.value)) for r in results]
    affected=[r['affected'] for _,r in values]
    status='AFFECTED' if all(v is True for v in affected) else 'NOT_AFFECTED' if all(v is False for v in affected) else 'UNKNOWN'
    return VersionMatchResult(status=status,affected=True if status=='AFFECTED' else False if status=='NOT_AFFECTED' else None,
        reason='All confirmed exact-package interval comparisons agree' if status!='UNKNOWN' else 'Version/range unsupported or comparisons disagree',
        claim_ids=tuple(c for c,_ in values),comparisons=tuple({'claim_id':c,**part} for c,r in values for part in r['comparisons']),
        normalization=values[0][1]['normalization'])


def _gate(context,asset_match):
    i=context.inputs;v=i.verification;unresolved=[]
    if v.verification_status!='CONFIRMED':unresolved.append('VERIFICATION_'+v.verification_status)
    if v.execution_status!='SUCCESS':unresolved.append('VERIFICATION_RUNTIME_INCOMPLETE')
    if i.investigation.runtime_status in ('FAILED','BLOCKED') or i.investigation.partial_result or i.investigation.status=='PARTIAL':
        unresolved.append('INVESTIGATION_INCOMPLETE')
    if v.partial_result or not i.coverage_complete or i.omitted_claim_count or i.omitted_evidence_count:
        unresolved.append('VERIFICATION_COVERAGE_INCOMPLETE')
    if i.source_verification_task=='conflict_detection':unresolved.append('CONFLICT_ONLY_NOT_FULL_VERIFICATION')
    if i.asset.context_status!='RESOLVED':unresolved.extend(i.asset.unresolved_items or ('ASSET_CONTEXT_MISSING',))
    if asset_match.status=='UNKNOWN':unresolved.append('ASSET_MATCH_UNKNOWN')
    checked={r.claim.claim_id:r for r in v.claims};valid={r.claim.claim_id for r in confirmed_claims(context)}
    relevant=[c for c in i.source_claims if c.claim_type=='AFFECTS_VERSION' and (
        asset_match.status!='MATCHED' or c.package_identifier_id in (None,i.asset.package_identifier_id) or
        value_matches_distribution(c.value,i.asset,required=True))]
    if not relevant:unresolved.append('IMPACT_CLAIM_MISSING')
    for c in relevant:
        if asset_match.status=='MATCHED' and c.package_identifier_id!=i.asset.package_identifier_id:
            unresolved.append('IMPACT_IDENTITY_UNRESOLVED:'+c.claim_id)
        if c.claim_id not in checked:unresolved.append('UNCHECKED_IMPACT:'+c.claim_id)
        elif c.claim_id not in valid:unresolved.append('UNCONFIRMED_IMPACT:'+c.claim_id)
    return unresolved


def _severity(context,claims):
    from cvss.exceptions import CVSSError
    bands=[];used=[];warnings=[]
    for r in claims:
        c=r.claim
        if c.claim_type!='CVSS_SCORE':continue
        value=c.value;band=value.get('severity','unknown');version=value.get('version');score=value.get('score')
        try:
            if value.get('vector'):
                from app.normalizers.common import metric
                vector_version=value['vector'].split('/')[0].removeprefix('CVSS:') if value['vector'].startswith('CVSS:') else '2.0'
                if version is not None and version!=vector_version:raise ValueError('CVSS vector/version mismatch')
                computed=metric(value['vector'],provider='sealed_claim',locator={},version=version)
                if score is not None and (isinstance(score,bool) or float(score)!=computed['base_score']):
                    raise ValueError('CVSS vector/score mismatch')
                if band!='unknown' and band!=computed['severity']:raise ValueError('CVSS vector/band mismatch')
                score=computed['base_score'];version=computed['version'];band=computed['severity']
            if version not in ('2.0','3.0','3.1','4.0') or isinstance(score,bool):raise ValueError('CVSS version/type invalid')
            score=float(score)
            if not math.isfinite(score) or not 0<=score<=10 or round(score,1)!=score:raise ValueError('CVSS score invalid')
            # Validate an explicitly verified band; never infer a band from a score-only claim.
            bounds={'low':(0,3.9),'medium':(4,6.9),'high':(7,10)} if version=='2.0' else {
                'info':(0,0),'low':(0.1,3.9),'medium':(4,6.9),'high':(7,8.9),'critical':(9,10)}
            if band not in bounds or not bounds[band][0]<=score<=bounds[band][1]:raise ValueError('CVSS band unconfirmed or inconsistent')
            bands.append(band);used.append(r)
        except (ValueError,KeyError,TypeError,AttributeError,CVSSError):
            warnings.append('CVSS_UNUSABLE:'+c.claim_id+': source value invalid, inconsistent or band unconfirmed')
    if len(set(bands))>1:warnings.append('CVSS_BAND_AMBIGUOUS: no severity selected')
    return bands[0] if bands and len(set(bands))==1 else 'unknown',tuple(used),tuple(warnings)


def _epss(context):
    result=[];now=context.evaluation_time.date()
    for item in context.inputs.epss:
        try:
            score=float(item.get('score'));observed=date.fromisoformat(str(item.get('score_date')))
            usable=math.isfinite(score) and 0<=score<=1 and now-timedelta(days=7)<=observed<=now and bool(item.get('raw_document_id'))
        except (ValueError,TypeError):score=None;usable=False
        result.append({'score':score if usable else None,'observed_score':item.get('score'),
            'score_date':item.get('score_date'),'raw_document_id':item.get('raw_document_id'),
            'receipt_id':item.get('receipt_id'),'status':'SOURCE_ASSERTED' if usable else 'STALE_OR_INVALID',
            'influences_decision':False})
    return tuple(result)


def assess_risk(context):
    context=AnalysisContext.model_validate_json(context.model_dump_json())
    i=context.inputs;v=i.verification;asset=i.asset;confirmed=confirmed_claims(context)
    am=match_asset(context);vm=match_version(context,am)
    refs={e.evidence_id:e for e in v.supporting_evidence}
    kev=tuple(r for r in confirmed if r.claim.claim_type=='KNOWN_EXPLOITED' and r.claim.value.get('known_exploited') is True
        and any(refs[e].source_key=='CISA_KEV' and refs[e].evidence_type=='kev_record' for e in r.supporting_evidence_ids))
    poc=tuple(r for r in confirmed if r.claim.claim_type in ('POC_EXISTS','POC_ASSOCIATION')
        and claim_applies_to_distribution(r.claim,asset))
    fixes=tuple(r for r in confirmed if r.claim.claim_type in ('FIXED_VERSION','PATCH_EXISTS','FIX_COMMIT')
        and r.claim.package_identifier_id==asset.package_identifier_id and
        claim_applies_to_distribution(r.claim,asset,require_identity=r.claim.claim_type=='FIXED_VERSION'))
    epss=_epss(context);band,severities,cvss_warnings=_severity(context,confirmed)
    status='KNOWN_EXPLOITED' if kev else 'VERIFIED_POC_ASSOCIATION' if poc else 'POC_CANDIDATE' if i.investigation.poc_candidates else 'UNKNOWN'
    signals=kev or poc
    exploitation=ExploitationSignal(status=status,claim_ids=tuple(r.claim.claim_id for r in signals),
        evidence_ids=tuple(sorted({e for r in signals for e in r.supporting_evidence_ids})),epss=epss)
    patch=PatchAvailability(status='CONFIRMED_PRESENT' if fixes else 'UNCONFIRMED' if i.investigation.patch_information or i.investigation.fixed_versions else 'UNKNOWN',
        claim_ids=tuple(r.claim.claim_id for r in fixes),evidence_ids=tuple(sorted({e for r in fixes for e in r.supporting_evidence_ids})))
    problems=_gate(context,am)
    factors=[];mitigating=[]
    def add(code,reason,value,rs=(),provenance='verified_claim',influences=True):
        f=RiskFactor(factor_id=code,code=code,reason=reason,value=value,claim_ids=tuple(r.claim.claim_id for r in rs),
            evidence_ids=tuple(sorted({e for r in rs for e in r.supporting_evidence_ids})),provenance=provenance,
            influences_decision=influences and not bool(problems))
        factors.append(f);return f
    if vm.status=='AFFECTED':add('VERIFIED_IMPACT','已核验的同发行包影响范围命中当前库存版本。',True,
                              tuple(r for r in confirmed if r.claim.claim_id in vm.claim_ids))
    if band!='unknown':add('VERIFIED_SEVERITY','已核验严重程度为 '+band,band,severities)
    if kev:add('KNOWN_EXPLOITED_KEV','已确认 CISA KEV 已知利用记录；不表示对本资产进行了利用测试。',True,kev)
    if poc:add('VERIFIED_POC_ASSOCIATION','仅确认公开 PoC 静态关联；可用性未经测试。',True,poc)
    if i.investigation.poc_candidates:add('POC_CANDIDATE','调查发现 PoC 候选，未据此确认可利用。',len(i.investigation.poc_candidates),
                                        provenance='candidate',influences=False)
    if epss:add('EPSS_SOURCE_ASSERTION','已有来源概率快照，仅供背景参考，未获得核验 Claim。',epss,
                provenance='source_assertion',influences=False)
    if fixes:add('REMEDIATION_AVAILABLE','存在已确认处置依据；没有资产已应用补丁的证明。',True,fixes)
    if asset.exposure=='internet':add('INTERNET_EXPOSED','用户库存标注外网暴露，未执行扫描。',True,provenance='asset_inventory')
    if asset.environment=='production':add('PRODUCTION','用户库存标注生产环境，不能据此推断资产重要性。',True,provenance='asset_inventory',influences=False)
    add('CRITICALITY_UNKNOWN','库存未提供已验证的重要性字段。','unknown',provenance='asset_inventory',influences=False)
    rule='R0_ABSTAIN';level='UNKNOWN';priority='REVIEW_REQUIRED';affected=None;details={}
    if not problems:
        if am.status=='NOT_MATCHED' or vm.status=='NOT_AFFECTED':
            rule='R1_SCOPED_LOW';level='LOW';priority='DEFER';affected=False
            f=add('NOT_AFFECTED_IN_SCOPE','仅本次所选组件/漏洞范围不命中，不表示整个资产安全。',False,
                  tuple(r for r in confirmed if r.claim.claim_id in am.claim_ids))
            factors.remove(f);mitigating.append(f)
            details=assess_priority({'match_status':'NOT_AFFECTED','verification_status':v.verification_status})
        elif vm.status=='UNKNOWN':problems.append('VERSION_MATCH_UNKNOWN')
        else:
            affected=True
            if kev and asset.exposure=='internet':rule='R2_EXPLOITED_EXPOSED';level='CRITICAL'
            elif kev:rule='R3_EXPLOITED';level='HIGH'
            elif band in ('critical','high') or poc:rule='R4_SEVERITY_OR_ASSOCIATION';level='HIGH'
            elif band in ('medium','low','info'):rule='R5_SUPPORTED_MODERATE';level='MEDIUM'
            else:rule='R6_MISSING_SEVERITY';problems.append('VERIFIED_SEVERITY_MISSING')
            if level!='UNKNOWN':
                details=assess_priority({'match_status':'AFFECTED','verification_status':v.verification_status,
                    'severity':band,'kev':{'confirmed':bool(kev)},'poc':{'confirmed':bool(poc)},'epss':{'score':None},
                    'remediation':{'statuses':['FIXED_VERSION_AVAILABLE' if r.claim.claim_type=='FIXED_VERSION' else
                        'VENDOR_GUIDANCE_AVAILABLE' if r.claim.claim_type=='VENDOR_CONFIRMED' else 'PATCH_AVAILABLE' for r in fixes]},
                    'environment':asset.environment,'exposure':asset.exposure})
                priority=details['priority']
    if problems and rule!='R6_MISSING_SEVERITY':
        vm=VersionMatchResult(reason='Impact conclusion withheld: '+','.join(problems),comparisons=vm.comparisons,
                              normalization=vm.normalization,claim_ids=vm.claim_ids)
    confidence=min((r.confidence for r in confirmed if r.claim.claim_id in set(vm.claim_ids)|
        {r.claim.claim_id for r in (*kev,*poc,*severities)}),default=0)
    if level=='UNKNOWN':confidence=min(confidence,0.49)
    if asset.context_status!='RESOLVED' or v.verification_status=='INSUFFICIENT_EVIDENCE':confidence=0
    used={e for f in (*factors,*mitigating) for e in f.evidence_ids}
    evidence_refs=tuple({'evidence_id':e.evidence_id,'claim_id':e.claim_id,'reference':e.reference,
        'raw_document_id':str(e.raw_document_id) if e.raw_document_id else None,'hash':e.hash,
        'source_key':e.source_key,'source_time':e.source_time.isoformat() if e.source_time else None,
        'verification_source_artifact_id':str(v.artifact_id)} for e in v.supporting_evidence if e.evidence_id in used)
    dispositions=tuple({'claim_id':r.claim.claim_id,'claim_type':r.claim.claim_type,'status':r.status,
        'used_as_verified_fact':r in confirmed,'supporting_evidence_ids':r.supporting_evidence_ids,
        'conflicting_evidence_ids':r.conflicting_evidence_ids} for r in v.claims)
    warnings=tuple(dict.fromkeys((*i.warnings,*v.warnings,*i.investigation.uncertainties,*cvss_warnings,
        'AS_OF_SNAPSHOT: 历史输入与库存快照，不保证实时状态。',*(('POC_NOT_EXECUTED',) if poc else ()))))
    return RiskAssessment(verification_status=v.verification_status,asset_id=asset.asset_id,component=asset.component,
        version=asset.deployed_version,asset_match_status=am.status,version_match_status=vm.status,
        asset_match_result=am,version_match_result=vm,exploitation_signal=exploitation,patch_availability=patch,
        risk_level=level,priority=priority,affected=affected,risk_factors=tuple(factors),mitigating_factors=tuple(mitigating),
        evidence_refs=evidence_refs,claim_dispositions=dispositions,confidence=confidence,
        reasoning_summary='本次固定范围风险为 '+level+'，处置优先级 '+priority+'。'+
            ('依据不足或有冲突，不能认定受影响或安全。' if affected is None else '仅所选组件/漏洞版本范围不受影响。' if affected is False else '已确认版本命中；风险和优先级分别按规则计算。'),
        warnings=warnings,unresolved_items=tuple(dict.fromkeys((*problems,*v.unresolved_items,*asset.unresolved_items))),
        rule_ids=(rule,),priority_details=details,partial_result=v.partial_result or not i.coverage_complete,
        coverage_complete=i.coverage_complete)
