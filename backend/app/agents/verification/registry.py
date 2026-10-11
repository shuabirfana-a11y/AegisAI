from app.agents.contracts import AgentContract
from app.agents.registry import AgentRegistry
from app.agents.interfaces import VerificationAgent
from app.agents.verification.roles import TOOLS,REGISTRY_VERSION


def create_verification_registry(implementation=None):
    from app.agents.verification.agent import EvidenceVerificationAgent
    registry=AgentRegistry(version=REGISTRY_VERSION)
    registry.register(AgentContract(agent_id='verification_agent',agent_type='verification',
        description='Read-only, rule-led verification of sealed investigation evidence',
        supported_tasks=tuple(TOOLS),allowed_tools=tuple(TOOLS.values())),VerificationAgent,
        implementation if implementation is not None else EvidenceVerificationAgent())
    return registry
