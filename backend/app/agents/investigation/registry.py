from app.agents.contracts import AgentContract
from app.agents.registry import AgentRegistry
from app.agents.interfaces import InvestigationAgent
from app.agents.investigation.roles import ROLES,REGISTRY_VERSION

def create_investigation_registry(implementation=None):
    registry=AgentRegistry(version=REGISTRY_VERSION)
    registry.register(AgentContract(agent_id='investigation_agent',agent_type='investigation',
        description='Read-only intelligence investigation; source assertions remain unverified',
        supported_tasks=tuple(ROLES),allowed_tools=tuple(sorted(set().union(*(r.tools for r in ROLES.values()))))),
        InvestigationAgent,implementation)
    return registry

