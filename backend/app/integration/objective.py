"""Original request scope, never a model's possibly narrowed objective."""
import re
from app.planner.schemas import PlannerInput
from app.integration.contracts import ObjectiveContract
from app.integration.profiles import REQUIREMENTS,minimum_outcomes,is_overview
from app.integration.rules_common import check,finish,grounded,assessments

def from_planner_input(input,profile):
    p=PlannerInput.model_validate(input.model_dump(mode='json') if isinstance(input,PlannerInput) else input)
    q=p.query;question=q.question
    targets=tuple(dict.fromkeys(([q.target] if q.target else [])+re.findall(r'\bCVE-\d{4}-\d{4,}\b',question.upper())))
    component=p.component
    days=re.findall(r'(?:近|最近|过去)\s*(\d+)\s*天',question)
    parsed_days=tuple(int(value) for value in days)
    gaps=[]
    if len(targets)!=1:gaps.append('SINGLE_TARGET_SCOPE_REQUIRED')
    if len(days)>1:gaps.append('AMBIGUOUS_TIME_SCOPE')
    if any(not 1<=value<=365 for value in parsed_days):gaps.append('UNSUPPORTED_TIME_SCOPE')
    if profile!='overview_v1' and not q.asset_id:gaps.append('ASSET_SCOPE_MISSING')
    outcomes=list(minimum_outcomes(profile,question))
    if re.search(r'具体.*(?:修复版本|补丁)|精确.*(?:修复|版本)',question):outcomes.append('precise_remediation')
    if re.search(r'(?:实际|验证).*(?:利用|PoC|POC)',question):outcomes.append('verified_exploitation')
    return ObjectiveContract(question=question,targets=targets,asset_id=q.asset_id,component_id=p.component_id,
        package_name=(component.package_name or component.name) if component else None,version=component.version if component else None,
        required_outcomes=tuple(outcomes),window_days=parsed_days[0] if len(parsed_days)==1 and 1<=parsed_days[0]<=365 else None,
        requires_current=bool(re.search(r'当前|最新|实时|现在',question) or q.realtime),scope_gaps=tuple(gaps))

def coverage(c):
    from app.integration.contracts import ObjectiveCoverage
    o=c.objective;r=c.analysis;i=c.investigation;items=[]
    if not o:return ()
    for outcome in o.required_outcomes:
        status='MISSING';refs=()
        if outcome=='identity' and i and i.canonical_id and o.targets==(i.canonical_id,):status='SATISFIED';refs=(str(i.artifact_id),)
        if outcome=='overview' and i and i.canonical_id:
            status='SATISFIED';refs=(str(i.artifact_id),)
        if outcome=='asset' and r and c.asset_snapshot and r.asset_id==o.asset_id and c.asset_snapshot.context_status=='RESOLVED':status='SATISFIED';refs=(str(r.artifact_id),)
        if outcome=='version_impact' and r and r.affected is not None and r.verification_status=='CONFIRMED' and r.version_match_status!='UNKNOWN':status='SATISFIED';refs=(str(r.artifact_id),)
        if outcome=='remediation_status' and r:
            status='SATISFIED' if r.patch_availability.status=='CONFIRMED_PRESENT' else 'ABSTAINED';refs=(str(r.artifact_id),)
        if outcome=='precise_remediation' and r and any(a.fixed_version or a.patch_reference for a in r.recommended_actions):status='SATISFIED';refs=(str(r.artifact_id),)
        if outcome=='risk' and r and r.risk_level!='UNKNOWN':status='SATISFIED';refs=(str(r.artifact_id),)
        if outcome=='priority' and r and r.priority!='REVIEW_REQUIRED':status='SATISFIED';refs=(str(r.artifact_id),)
        # Static PoC association/KEV is not proof of a successful exploit test.
        if outcome=='verified_exploitation':status='ABSTAINED'
        items.append(ObjectiveCoverage(outcome=outcome,status=status,references=refs))
    return tuple(items)

def check_objective(c):
    issues=[];o=c.objective;i=c.investigation;r=c.analysis;asset=c.asset_snapshot
    if o is None:return (check('objective','OBJECTIVE_CONTEXT_MISSING','Original request scope unavailable','REPLAN'),)
    for gap in o.scope_gaps:issues.append(check('objective',gap,'Original request scope incomplete','REPLAN'))
    if len(o.targets)!=1:issues.append(check('objective','TARGET_SCOPE_INCOMPLETE','Exactly one bounded vulnerability required','REPLAN'))
    if i and o.targets and (i.canonical_id not in o.targets):issues.append(check('objective','OBJECTIVE_TARGET_MISMATCH','Artifact is outside requested vulnerability scope','FATAL'))
    if asset:
        for expected,actual,code in ((o.asset_id,asset.asset_id,'OBJECTIVE_ASSET_MISMATCH'),
            (o.component_id,asset.component_id,'OBJECTIVE_COMPONENT_MISMATCH'),(o.version,asset.deployed_version,'OBJECTIVE_VERSION_MISMATCH'),
            (o.package_name,asset.package_name,'OBJECTIVE_PACKAGE_MISMATCH')):
            if expected is not None and expected!=actual:issues.append(check('objective',code,'Output scope differs from original input','FATAL'))
    for item in coverage(c):
        if item.status=='MISSING':issues.append(check('objective','OBJECTIVE_NOT_COVERED','Required '+item.outcome+' not answered','REPLAN',objective=item.outcome))
        elif item.status=='ABSTAINED':
            exact=item.outcome in ('precise_remediation','verified_exploitation','version_impact')
            issues.append(check('objective','REQUIRED_DETERMINATION_UNAVAILABLE' if exact else 'REMEDIATION_UNKNOWN',
                'No justified definitive conclusion; disclosed unknown','REPLAN' if exact else 'NONE',warning=not exact,objective=item.outcome))
    if is_overview(c) and ((r and r.risk_level=='UNKNOWN') or (c.verification and c.verification.verification_status!='CONFIRMED')):
        issues.append(check('objective','OVERVIEW_BOUNDED_ABSTENTION','Overview reports existing facts with explicit unknowns',warning=True))
    return finish('objective',issues)
