"""Compose existing synchronous services with request-local execution control."""
from app.planner.schemas import PlannerInput
from app.runtime.contracts import TaskPlan
from app.agents.investigation.service import IntelligenceInvestigationService
from app.agents.verification.service import EvidenceVerificationService
from app.agents.analysis.service import SecurityAnalysisService
from app.integration.service import IntegrationService,GateControl
from app.orchestration.control import ControlledGateway
from sqlalchemy import select
from app.db import models as m
from app.db.session import transaction


class AgentServices:
    def __init__(self,engine,gateway,control):
        self.control=control
        self.investigator=IntelligenceInvestigationService(engine,ControlledGateway(gateway,control),observer=control)
        self.verifier=EvidenceVerificationService(engine)
        self.analyzer=SecurityAnalysisService(engine)
        self.gate=IntegrationService(engine)
        for svc,stage in ((self.investigator,'INVESTIGATING'),(self.verifier,'VERIFYING'),(self.analyzer,'ANALYZING')):
            svc.runtime.bind_execution_control(control.for_stage(stage))

    def investigate(self,scope,key,actor):
        self.control.check_start()
        raw=scope.planner_input.model_dump(mode='json');raw['query']['request_key']=key
        input=PlannerInput.model_validate(raw)
        saved=self.investigator.plan_and_run(input,actor)
        if saved.planning_status!='VALIDATED' or saved.runtime_run_id is None:return saved,None,None
        # Use the actual bound plan, including server-created role bindings.
        # The earlier Planner candidate is deliberately still unbound.
        with transaction(self.investigator.runtime.engine) as db:
            row=db.scalar(select(m.AgentRun).where(m.AgentRun.id==saved.runtime_run_id,
                m.AgentRun.actor_principal==actor,m.AgentRun.agent_type=='runtime-v1'))
            if row is None:raise LookupError('Run not found')
            plan=TaskPlan.model_validate(row.details['runtime_v1']['plan'])
        return saved,self.investigator.read_results(saved.runtime_run_id,actor),plan

    def verify(self,request,actor):
        self.control.check_start();saved=self.verifier.run(request,actor=actor)
        return self.verifier.read_results(saved.run_id,actor=actor)

    def analyze(self,request,actor):
        self.control.check_start();saved=self.analyzer.run(request,actor=actor)
        return self.analyzer.read_results(saved.run_id,actor=actor)

    def integrate(self,request,actor):
        self.control.check_start()
        return self.gate.evaluate(request,actor=actor,control=GateControl(
            cancel_event=self.control.cancel_event,deadline_monotonic=self.control.deadline))
