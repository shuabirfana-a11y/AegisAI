"""Tool metadata is derived, never maintained as a competing registry."""
from app.tooling.contracts import REGISTRY, ToolEnvelope
from app.runtime.contracts import ToolContract


def tool_contract(name: str, timeout_seconds: float) -> ToolContract:
    spec = REGISTRY.get(name)
    if spec is None:
        raise ValueError('Unknown registered tool')
    return ToolContract(name=name, description=spec.description,
                        input_schema=spec.input.model_json_schema(),
                        output_schema=ToolEnvelope.model_json_schema(),
                        permission=spec.permission, timeout=timeout_seconds)
