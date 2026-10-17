"""Read-only preflight of required context; no model, inventory or verdict access."""
from typing import Literal
from pydantic import Field,model_validator
from app.runtime.contracts import FrozenModel
from app.orchestration.scope import resolve_scope
from app.agents.investigation.normalization import normalize_question

MissingField=Literal['vulnerability_id','component','version','asset_context']


class ContextResolution(FrozenModel):
    status:Literal['READY','LIMITED_INVESTIGATION','NEED_CONTEXT']
    missing_fields:tuple[MissingField,...]=Field(default=(),max_length=4)
    version:Literal['context-check-v1']='context-check-v1'

    @model_validator(mode='after')
    def consistent(self):
        if (self.status=='NEED_CONTEXT')!=bool(self.missing_fields):
            raise ValueError('CONTEXT_RESOLUTION_INCONSISTENT')
        return self


def check_context(request,*,actor):
    scope=resolve_scope(request,actor=actor);p=scope.planner_input
    original=request.planner_input
    # Legacy scope inference is not deployment evidence. Preserve original nulls
    # and let the literal normalizer exclude advisory/fixed/range versions.
    normalized=normalize_question(original.query.question,{'targets':scope.targets,
        'component':original.component.model_dump(mode='json') if original.component else None},
        {k:str(v) for k,v in {'asset_id':p.query.asset_id,'component_id':p.component_id,
         'snapshot_id':p.snapshot_id}.items() if v})
    outcomes=set(scope.objective.required_outcomes)
    implicit_risk=(request.investigation_options.objective_profile is None and
        normalized.task_type=='asset_risk')
    risk=scope.objective_profile=='asset_risk_v1' or bool(outcomes&{'risk','priority'}) or implicit_risk
    deployment=scope.objective_profile=='asset_impact_v1' or risk or 'version_impact' in outcomes
    missing=[]
    version=normalized.version
    if version is not None and version.strip().casefold() in ('','unknown','未知'):
        version=None
    captured_component=p.component is not None and bool(p.component.name.strip())
    captured_version=(captured_component and version is not None and p.component.version==version)
    if deployment:
        if not scope.targets:missing.append('vulnerability_id')
        if not captured_component:missing.append('component')
        if not captured_version:missing.append('version')
        if risk and not p.query.asset_id:missing.append('asset_context')
    elif p.component is not None and scope.targets and not captured_version:
        # Existing Validator requires version input for a scoped component;
        # selecting overview must not conceal that requirement.
        missing.append('version')
    # Broad fact discovery may use registered public search tools. It is not a
    # deployment conclusion and still goes through the original Planner/Gate.
    status='NEED_CONTEXT' if missing else 'READY' if scope.targets else 'LIMITED_INVESTIGATION'
    return ContextResolution(status=status,missing_fields=tuple(missing))
