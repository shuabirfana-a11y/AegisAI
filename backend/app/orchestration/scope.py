"""Adapt bounded original scope; model plans never grant scope or authority."""
import re
from uuid import uuid4
from app.assistant.router import route
from app.planner.context import build_context
from app.planner.schemas import PlannerInput
from app.runtime.contracts import RuntimePolicy
from app.tooling.contracts import ResolutionInput
from app.integration.objective import from_planner_input
from app.integration.profiles import minimum_outcomes
from app.integration.contracts import ObjectiveContract
from app.orchestration.contracts import capture_request, ResolvedScope, valid_actor


def resolve_scope(request,*,actor):
    valid_actor(actor);request=capture_request(request);original=request.planner_input
    q=original.query
    textual=tuple(dict.fromkeys(re.findall(r'(?<![A-Z0-9_])CVE-\d{4}-\d{4,}(?![A-Z0-9_])',q.question.upper())))
    if len(textual)>3:raise ValueError('TARGET_SCOPE_LIMIT')
    if q.target and textual and q.target not in textual:raise ValueError('TARGET_SCOPE_CONFLICT')
    routed=route(q.question,target=q.target,asset_id=q.asset_id,mode=q.mode)
    if routed['blocked']:raise ValueError('REQUEST_BLOCKED')
    inferred=build_context(PlannerInput(query=q),actor,RuntimePolicy(),uuid4(),uuid4()).scope['component']
    component=original.component;origin='EXPLICIT' if component else 'MISSING'
    if inferred:
        if component:
            if component.name.casefold()!=inferred['name'].casefold() or (
                    component.version is not None and component.version!=inferred['version']):
                raise ValueError('COMPONENT_SCOPE_CONFLICT')
            if component.version is None:
                component=ResolutionInput.model_validate({**component.model_dump(),'version':inferred['version']})
        else:
            component=ResolutionInput.model_validate(inferred);origin='QUESTION_EXTRACTED'
    raw=original.model_dump(mode='json');raw['component']=component.model_dump(mode='json') if component else None
    if not q.target and len(textual)==1:raw['query']['target']=textual[0]
    captured=PlannerInput.model_validate(raw)
    profile=request.investigation_options.objective_profile
    if profile is None:
        profile=('asset_risk_v1' if re.search(r'风险(?:分析|判断|等级|评估)|优先级',q.question)
                 else 'asset_impact_v1' if q.asset_id or original.component_id or routed['asset'] or component
                 else 'overview_v1')
    objective=from_planner_input(captured,profile);value=objective.model_dump(mode='json')
    gaps=list(objective.scope_gaps);explicit=False
    # The reused objective parser supports Arabic relative day windows only.
    # Preserve unsupported explicit temporal intent as a blocking scope gap,
    # without mistaking a CVE year or a component version for a calendar date.
    remaining_time=re.sub(r'(?:近|最近|过去)\s*\d+\s*天','',q.question)
    unsupported_time=(r'\d{4}年|(?<![A-Za-z0-9-])\d{4}[-/]\d{1,2}[-/]\d{1,2}(?!\d)|'
        r'(?:近|最近|过去)\s*[\d零〇一二两三四五六七八九十百半]+\s*(?:个?月|天|日|周|星期|年|小时)|'
        r'(?:上|下)(?:个)?(?:周|月|星期)|昨天|前天|今年|去年|本月|本周')
    if re.search(unsupported_time,remaining_time):gaps.append('UNSUPPORTED_TIME_SCOPE')
    all_targets=tuple(dict.fromkeys(([q.target] if q.target else [])+list(textual)))
    if all_targets!=objective.targets:
        value['targets']=all_targets;explicit=True
        if len(all_targets)!=1:gaps.append('SINGLE_TARGET_SCOPE_REQUIRED')
    if original.snapshot_id:gaps.append('SNAPSHOT_SCOPE_NOT_SUPPORTED')
    if re.search(r'(?i)POC|公开.{0,5}(代码|利用)',q.question):
        gaps.append('POC_COMPLETENESS_NOT_SUPPORTED')
    versions=re.findall(r'\b(?:vllm|mlflow|pytorch|torch|langchain|transformers)\s+([0-9]+(?:\.[0-9]+){1,3}[a-zA-Z0-9.+-]*)',q.question,re.I)
    if len(versions)>1:gaps.append('AMBIGUOUS_COMPONENT_SCOPE')
    if request.time_scope:
        time=request.time_scope
        if time.window_days is not None:
            if objective.window_days is not None and time.window_days!=objective.window_days:
                raise ValueError('TIME_SCOPE_CONFLICT')
            value['window_days']=time.window_days
        value['requires_current']=objective.requires_current or time.requires_current
        explicit=True
    value['scope_gaps']=tuple(dict.fromkeys(gaps))
    if value['scope_gaps']!=objective.scope_gaps:explicit=True
    # The profile's minimum outcomes always include the actual question's intent.
    if not set(minimum_outcomes(profile,q.question))<=set(value['required_outcomes']):
        raise ValueError('OBJECTIVE_PROFILE_WEAKENED')
    return ResolvedScope(planner_input=captured,targets=tuple(value['targets']),component_origin=origin,
        objective_profile=profile,objective_source='new_structured_request' if explicit else 'stored_planner_request',
        objective=ObjectiveContract.model_validate(value),route=routed)
