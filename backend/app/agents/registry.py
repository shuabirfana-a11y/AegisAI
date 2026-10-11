"""Explicit server-owned registration with immutable, serializable snapshots."""
from dataclasses import dataclass
import json
from app.agents.contracts import AgentContract, AgentFrameworkError, REGISTRY_VERSION, fingerprint
from app.agents.interfaces import ProfessionalAgent, InvestigationAgent, VerificationAgent, SecurityAnalysisAgent
from app.planner.registry import TASK_REGISTRY


@dataclass(frozen=True)
class AgentRegistration:
    contract_json: str
    interface: type[ProfessionalAgent]
    implementation: ProfessionalAgent | None
    implementation_key: str

    @property
    def contract(self) -> AgentContract:
        return AgentContract.model_validate_json(self.contract_json)


@dataclass(frozen=True)
class RegistrySnapshot:
    entries: tuple[AgentRegistration, ...]
    metadata_json: str
    fingerprint: str

    @property
    def metadata(self): return json.loads(self.metadata_json)

    def get(self, agent_id: str) -> AgentRegistration | None:
        return next((r for r in self.entries if r.contract.agent_id == agent_id), None)

    def for_task(self, semantic_type: str) -> AgentRegistration | None:
        return next((r for r in self.entries if semantic_type in r.contract.supported_tasks), None)


class AgentRegistry:
    def __init__(self, *, version=REGISTRY_VERSION):
        self.version = version
        self._entries: dict[str, AgentRegistration] = {}

    def register(self, contract: AgentContract, interface: type[ProfessionalAgent],
                 implementation: ProfessionalAgent | None = None) -> None:
        contract = AgentContract.model_validate_json(contract.model_dump_json())
        expected = {'investigation': InvestigationAgent, 'verification': VerificationAgent,
                    'security_analysis': SecurityAnalysisAgent}[contract.agent_type]
        if not isinstance(interface, type) or not issubclass(interface, expected):
            raise AgentFrameworkError('AGENT_INTERFACE_INVALID')
        if contract.agent_id in self._entries or any(set(contract.supported_tasks) & set(r.contract.supported_tasks)
                                                    for r in self._entries.values()):
            raise AgentFrameworkError('AGENT_REGISTRATION_CONFLICT')
        key = 'interface_only'
        if implementation is not None:
            key = getattr(implementation, 'implementation_key', '')
            if not isinstance(implementation, interface) or not isinstance(key, str) or not 1 <= len(key) <= 100 or key == 'interface_only':
                raise AgentFrameworkError('AGENT_IMPLEMENTATION_INVALID')
        self._entries[contract.agent_id] = AgentRegistration(contract.model_dump_json(), interface, implementation, key)

    def freeze(self) -> RegistrySnapshot:
        entries = tuple(self._entries[k] for k in sorted(self._entries))
        metadata = {'registry_version': self.version, 'agents': [
            {'contract': r.contract.model_dump(mode='json'), 'implementation_key': r.implementation_key}
            for r in entries]}
        return RegistrySnapshot(entries, json.dumps(metadata, ensure_ascii=False), fingerprint(metadata))


def create_default_registry() -> AgentRegistry:
    registry = AgentRegistry()
    for agent_id, kind, interface, tasks in (
        ('investigation_agent', 'investigation', InvestigationAgent,
         ('vulnerability_lookup','version_match','patch_analysis')),
        ('verification_agent', 'verification', VerificationAgent, ('evidence_search',)),
        ('security_analysis_agent', 'security_analysis', SecurityAnalysisAgent, ('risk_analysis',))):
        tools = sorted({tool for task in tasks for tool in TASK_REGISTRY[task].tools})
        registry.register(AgentContract(agent_id=agent_id, agent_type=kind,
            description='Registered capability interface; security implementation is not installed',
            supported_tasks=tasks, allowed_tools=tools), interface)
    return registry
