from typing import Literal
from pydantic import ConfigDict, Field
from app.runtime.contracts import TaskContract
from app.planner.schemas import PlannerPlan

InvestigationTaskType=Literal['vulnerability_lookup','evidence_search','asset_lookup']
class InvestigationTaskCandidate(TaskContract):
    model_config=ConfigDict(extra='forbid',frozen=True,allow_inf_nan=False,populate_by_name=True)
    planner_type:InvestigationTaskType=Field(alias='type')

class InvestigationPlan(PlannerPlan):
    tasks:tuple[InvestigationTaskCandidate,...]=Field(min_length=1,max_length=16)

