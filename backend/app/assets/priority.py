"""Published deterministic tiers, no composite/AI risk score."""
RULE_VERSION='asset-priority-v1'
HIGH_EPSS=0.5

def assess_priority(context):
    factors=[]
    def add(code,reason,value=True):factors.append({'code':code,'reason':reason,'value':value})
    status=context['match_status'];severity=context.get('severity','unknown')
    kev=context.get('kev',{}).get('confirmed',False);poc=context.get('poc',{}).get('confirmed',False)
    score=context.get('epss',{}).get('score');high_epss=score is not None and score>=HIGH_EPSS
    fixes=context.get('remediation',{}).get('statuses',[])
    if status=='AFFECTED':add('ASSET_MATCH','Current installed version matches a verified package-specific range')
    if severity in ('critical','high'):add('HIGH_SEVERITY','Published severity is '+severity,severity)
    if kev:add('KEV','Confirmed CISA KEV listing')
    if poc:add('CONFIRMED_POC','Verified public PoC association; execution/usability not evaluated')
    if high_epss:add('HIGH_EPSS','EPSS exceeds the documented0.5 threshold',score)
    for fix in fixes:
        if fix in ('PATCH_AVAILABLE','FIXED_VERSION_AVAILABLE','VENDOR_GUIDANCE_AVAILABLE'):add(fix,'Current evidence supports this remediation option')
    if context.get('environment')=='production':add('PRODUCTION','User marked production environment')
    if context.get('exposure')=='internet':add('INTERNET_EXPOSED','User marked internet exposure; no scan performed')
    if context.get('verification_status')=='CONFLICT':add('INTELLIGENCE_CONFLICT','Current version assertions disagree')
    if status in ('UNCERTAIN','NOT_EVALUATED'):
        priority='REVIEW';action='Confirm package/version and resolve intelligence uncertainty'
    elif status=='NOT_AFFECTED':priority='INFO';action='No version impact within this evaluated vulnerability scope'
    elif kev:priority='P0';action='Prioritize mitigation immediately; use evidence-backed remediation'
    elif poc and severity in ('critical','high') or high_epss and severity in ('critical','high') or severity=='critical' and context.get('exposure')=='internet':
        priority='P1';action='Prioritize verified remediation'
    elif severity in ('critical','high') or poc or high_epss:priority='P2';action='Plan remediation for this affected component'
    else:priority='P3';action='Track and plan remediation according to available evidence'
    why='; '.join(f['reason'] for f in factors) or 'Available facts do not establish a definite version impact'
    return {'priority':priority,'risk_factors':factors,'factor_codes':[f['code'] for f in factors],'why_now':why,
        'recommended_action':action,'rule_version':RULE_VERSION,'high_epss_threshold':HIGH_EPSS}
