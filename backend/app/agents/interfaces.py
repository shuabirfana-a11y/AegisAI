"""Capability interfaces only: no security algorithm or provider invocation."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID
from app.runtime.contracts import ExecutionOutcome
if TYPE_CHECKING:
    from app.agents.artifacts import AgentExecutionRequest


class ProfessionalAgent(ABC):
    implementation_key: str

    @abstractmethod
    def for_run(self, run_id: UUID) -> 'ProfessionalAgent':
        """Create a run-owned implementation; cancellation must not cross runs."""
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: 'AgentExecutionRequest', *, database_url: str | None = None) -> ExecutionOutcome:
        raise NotImplementedError

    @abstractmethod
    def cancel_all(self) -> None:
        raise NotImplementedError


class InvestigationAgent(ProfessionalAgent):
    def execute(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        return self.investigate(request, database_url=database_url)

    @abstractmethod
    def investigate(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        raise NotImplementedError


class VerificationAgent(ProfessionalAgent):
    def execute(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        return self.verify(request, database_url=database_url)

    @abstractmethod
    def verify(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        raise NotImplementedError


class SecurityAnalysisAgent(ProfessionalAgent):
    def execute(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        return self.analyze(request, database_url=database_url)

    @abstractmethod
    def analyze(self, request: 'AgentExecutionRequest', *, database_url=None) -> ExecutionOutcome:
        raise NotImplementedError
