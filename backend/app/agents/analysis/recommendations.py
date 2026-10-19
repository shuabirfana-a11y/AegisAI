"""Grounded actions only; availability never proves a patch was deployed."""
from urllib.parse import urlsplit
from packaging.version import Version,InvalidVersion
from app.assets.versions import compare_version
from app.agents.analysis.rules import confirmed_claims,claim_applies_to_distribution
from app.agents.analysis.schemas import RecommendedAction


def _scoped_fix_applies(context,row,version_match):
    """A source-bound fix applies to its maintenance entry, not every union member."""
    from app.enrichment.version_scope import evidence_scopes,VersionScope
    from app.enrichment.versions import canonical_value
    from app.agents.contracts import fingerprint
    from app.assets.identity import _name
    asset=context.inputs.asset;c=row.claim
    selection=version_match.normalization.get('scope_resolution',{})
    if selection.get('method')!='VERIFIED_RECORD_UNION':return True
    if any(c.value.get(k) for k in ('condition','platform','architecture')):return False
    refs={e.evidence_id:e for e in context.inputs.verification.supporting_evidence}
    unions=[]
    for r in context.inputs.verification.claims:
        if r.claim.claim_id!=selection.get('claim_id'):continue
        for eid in r.supporting_evidence_ids:
            e=refs.get(eid)
            if e:
                unions.extend(VersionScope.model_validate(p) for p in evidence_scopes(e,'AFFECTS_VERSION'))
    proofs=[]
    for eid in row.supporting_evidence_ids:
        e=refs.get(eid)
        if not e or not e.details.get('normalized_version_scope'):continue
        if (not e.is_current or e.integrity_status!='VALID' or e.exclusion_reasons or
            e.stance!='support' or e.scope_key!=c.scope_key or e.vulnerability_id!=c.vulnerability_id):return False
        data=evidence_scopes(e,'FIXED_VERSION')
        if not data:return False
        for p in data:
            proof=VersionScope.model_validate(p)
            if (proof.value_hash!=fingerprint(canonical_value('FIXED_VERSION',c.value)) or
                proof.component!=c.value.get('package') or _name(proof.component,'PyPI')!=asset.package_name or
                proof.product!=c.value.get('product') or proof.fixed_version!=str(Version(c.value['version']))):return False
            if not any(u.coverage=='RECORD_UNION' and u.component==proof.component and
                u.product==proof.product and u.record_union==proof.record_union for u in unions):return False
            ranges=[]
            for lo,li,hi,ui in proof.predicate:
                if lo is not None and not li:return False
                events=[{'introduced':lo or '0'}]
                if hi is not None:events.append({'last_affected' if ui else 'fixed':hi})
                ranges.append({'events':events})
            if not ranges or compare_version(asset.deployed_version,{'ecosystem':'PyPI','ranges':ranges})['affected'] is not True:return False
            proofs.append(proof)
    return bool(proofs)


def build_actions(context,*,asset_match,version_match,risk_level,priority):
    inputs=context.inputs;asset=inputs.asset;actions=[]
    category='IMMEDIATE' if priority in ('P0','P1') else 'LONG_TERM_HARDENING'
    def general(kind,summary,cat='FURTHER_INVESTIGATION'):
        actions.append(RecommendedAction(action_id=kind,action_type=kind,category=cat,summary=summary,
            target_component=asset.component,action_provenance='GENERAL_PRECAUTION'))
    if priority=='REVIEW_REQUIRED':
        general('REQUEST_REVIEW','补充或复核资产、版本与冲突来源，未知不等于不受影响。')
    if priority=='DEFER':
        general('TRACK_SCOPED_STATUS','本次所选组件/漏洞范围不受影响；持续跟踪库存变化与公告。','LONG_TERM_HARDENING')
        return tuple(actions)
    trusted=confirmed_claims(context)
    ranges=[r.claim.value for r in trusted if r.claim.claim_id in version_match.claim_ids]
    normal=inputs.verification.verification_status=='CONFIRMED' and asset_match.status=='MATCHED'
    for r in trusted:
        c=r.claim
        if not normal or c.branch or c.value.get('branch'):continue
        scoped=c.package_identifier_id==asset.package_identifier_id
        if c.claim_type=='FIXED_VERSION' and scoped and version_match.status=='AFFECTED' and claim_applies_to_distribution(c,asset,require_identity=True):
            fixed=c.value.get('version')
            if not isinstance(fixed,str) or not ranges or not all(compare_version(fixed,value)['affected'] is False for value in ranges):continue
            try:
                if Version(fixed)<=Version(asset.deployed_version) or not _scoped_fix_applies(context,r,version_match):continue
            except (InvalidVersion,TypeError,ValueError):continue
            actions.append(RecommendedAction(action_id='fix:'+c.claim_id,action_type='UPGRADE_VERIFIED_RELEASE',
                category=category,summary='评估升级到已确认修复版本 '+fixed+'；先验证依赖与部署兼容性。',
                target_component=asset.component,fixed_version=fixed,claim_ids=(c.claim_id,),
                evidence_ids=r.supporting_evidence_ids,preconditions=('同发行包；先验证兼容性；尚无已部署修复的证明。',),
                action_provenance='VERIFIED_CLAIM',applicability='CONFIRMED'))
        if c.claim_type in ('PATCH_EXISTS','FIX_COMMIT'):
            if not claim_applies_to_distribution(c,asset):continue
            url=c.value.get('url') or c.value.get('patch_url')
            if not isinstance(url,str):continue
            parsed=urlsplit(url)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:continue
            # A static existence verdict is sufficient to inspect, not to claim installation/applicability.
            actions.append(RecommendedAction(action_id='patch:'+c.claim_id,action_type='INSPECT_PATCH_REFERENCE',
                category='FURTHER_INVESTIGATION',summary='检查已确认的补丁引用及发行包/分支适用性，再评估应用。',
                target_component=asset.component,patch_reference=url,claim_ids=(c.claim_id,),
                evidence_ids=r.supporting_evidence_ids,preconditions=('确认包/分支适用性和部署兼容性。',),
                action_provenance='VERIFIED_CLAIM',applicability='UNKNOWN'))
    if not any(a.fixed_version or a.patch_reference for a in actions):
        general('TRACK_REMEDIATION','当前没有可用于该组件的已确认修复依据；继续跟踪厂商公告，不能推断无补丁。')
    if asset.exposure=='internet' and priority!='REVIEW_REQUIRED':
        general('EVALUATE_EXPOSURE_RESTRICTION','评估临时限制所选服务的外网暴露，确认业务影响后由负责人执行。',category)
    general('MONITOR_COMPONENT','加强对所选组件的日志和异常行为监测；该方向不是厂商修复指令。','LONG_TERM_HARDENING')
    return tuple(actions)
