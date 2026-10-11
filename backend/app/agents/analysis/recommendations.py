"""Grounded actions only; availability never proves a patch was deployed."""
from urllib.parse import urlsplit
from app.assets.versions import compare_version
from app.agents.analysis.rules import confirmed_claims,claim_applies_to_distribution
from app.agents.analysis.schemas import RecommendedAction


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
