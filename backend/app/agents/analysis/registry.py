from app.agents.contracts import AgentContract
from app.agents.registry import AgentRegistry
from app.agents.interfaces import SecurityAnalysisAgent as AnalysisInterface
from app.agents.analysis.roles import TOOLS,REGISTRY_VERSION


def create_analysis_registry(implementation=None):
    from app.agents.analysis.agent import SecurityAnalysisAgent
    registry=AgentRegistry(version=REGISTRY_VERSION)
    registry.register(AgentContract(agent_id='security_analysis_agent',agent_type='security_analysis',
        description='Read-only deterministic analysis of sealed, verified intelligence and owned inventory',
        supported_tasks=tuple(TOOLS),allowed_tools=tuple(TOOLS.values())),AnalysisInterface,
        implementation if implementation is not None else SecurityAnalysisAgent())
    return registry
