"""Reconstruct professional chains from canonical, actor-owned persisted facts."""
from uuid import UUID
from pydantic import Field
from sqlalchemy import select
from app.agents.artifacts import AgentArtifact
from app.agents.contracts import AgentBinding, AgentRunTrace, ArtifactReference, AgentFrameworkError, fingerprint
from app.runtime.contracts import FrozenModel, TaskPlan, TaskTrace, TaskArtifact, TaskState
from app.db import models as m
from app.db.session import transaction


class ProfessionalTraceSnapshot(FrozenModel):
    run_id: UUID
    trace_id: UUID
    registry_version: str
    registry_fingerprint: str
    agents: tuple[AgentRunTrace, ...]
    artifacts: tuple[AgentArtifact, ...]


def reference(artifact: AgentArtifact) -> ArtifactReference:
    return ArtifactReference(**{k:v for k,v in artifact.model_dump().items() if k in ArtifactReference.model_fields})


class ProfessionalTraceStore:
    def __init__(self, engine): self.engine = engine

    def read(self, run_id: UUID, actor: str) -> ProfessionalTraceSnapshot:
        with transaction(self.engine) as db:
            row = db.scalar(select(m.AgentRun).where(m.AgentRun.id==UUID(str(run_id)),
                m.AgentRun.agent_type=='runtime-v1',m.AgentRun.actor_principal==actor))
            if row is None: raise LookupError('Run not found')
            ns = row.details['runtime_v1']
            plan = TaskPlan.model_validate(ns['plan'])
            professional = plan.route.get('professional_agents_v1')
            if professional is None: raise AgentFrameworkError('AGENT_TRACE_NOT_AVAILABLE')
            if fingerprint(professional['registry']) != professional['registry_fingerprint']:
                raise AgentFrameworkError('AGENT_TRACE_INVALID')
            bindings = {key:AgentBinding.model_validate(value) for key,value in professional['bindings'].items()}
            artifacts = {key:TaskArtifact.model_validate(value) for key,value in ns['artifacts'].items()}
            extended = {}
            for key,binding in bindings.items():
                if key in artifacts:
                    if artifacts[key].run_id != row.id: raise AgentFrameworkError('AGENT_TRACE_INVALID')
                    extended[key] = AgentArtifact.from_task_artifact(artifacts[key],binding)
            runs = []
            for task in plan.tasks:
                binding = bindings.get(task.task_id)
                if binding is None: continue
                if binding.task_fingerprint != fingerprint(task.model_dump(mode='json')):
                    raise AgentFrameworkError('AGENT_TRACE_INVALID')
                trace = TaskTrace.model_validate(ns['traces'][task.task_id])
                if trace.run_id != row.id or trace.task_id != task.task_id:
                    raise AgentFrameworkError('AGENT_TRACE_INVALID')
                attempted = trace.start_time is not None and trace.status != TaskState.BLOCKED
                inputs = tuple(reference(extended[key]) for key in task.dependencies
                    if attempted and key in extended and extended[key].status==TaskState.SUCCESS)
                elapsed = max(0,int((trace.end_time-trace.start_time).total_seconds()*1000)) if trace.start_time and trace.end_time else None
                output = extended.get(task.task_id)
                runs.append(AgentRunTrace(agent_id=binding.agent_id,agent_type=binding.agent_type,
                    task_id=task.task_id,run_id=row.id,input_artifact=inputs,
                    output_artifact=reference(output) if output else None,execution_time=elapsed,
                    status=trace.status,attempted=attempted,errors=trace.error,
                    capability_state='interface_only' if binding.implementation_key=='interface_only' else 'implementation_registered'))
            return ProfessionalTraceSnapshot(run_id=row.id,trace_id=row.details['trace_id'],
                registry_version=professional['registry']['registry_version'],
                registry_fingerprint=professional['registry_fingerprint'],agents=runs,
                artifacts=[extended[t.task_id] for t in plan.tasks if t.task_id in extended])
