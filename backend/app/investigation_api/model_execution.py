"""Read-only public projection of a stored Planner identity and call receipts."""
import json
from app.llm.schemas import CallRecord
from app.orchestration.contracts import InvestigationContext
from app.planner.trace import PlannerTraceStore
from app.investigation_api.projection import public_copy
from app.investigation_api.schemas import ModelExecutionMetadata


def read_model_execution(engine, context: InvestigationContext, *, actor: str) -> ModelExecutionMetadata | None:
    if actor != context.owner:
        raise LookupError('Planner run not found')
    if context.planner_run_id is None:
        return None
    trace = PlannerTraceStore(engine).read(context.planner_run_id, actor)
    if not trace.attempts:
        return None
    calls = tuple(CallRecord.model_validate_json(json.dumps(attempt.model_call, allow_nan=False))
                  for attempt in trace.attempts)
    identity = trace.model
    if (not 1 <= len(calls) <= 2 or identity.is_mock != (identity.provider == 'mock')
            or any(call.provider != identity.provider or call.requested_model != identity.model
                   or call.is_mock != identity.is_mock or call.function != 'generate_structured'
                   or (identity.is_mock and call.model != identity.model)
                   or call.trace_id != str(trace.trace_id) for call in calls)):
        raise ValueError('MODEL_EXECUTION_IDENTITY_MISMATCH')
    invoked = tuple(call for call in calls if call.attempt_count > 0)
    if not invoked:
        return None
    # Compatible APIs can return a canonical/versioned model for a requested alias.
    # Use the stored returned name, while requiring one consistent execution identity.
    # Receipts cannot distinguish a returned alias from the fallback used when
    # no model name was returned. Requested aliases remain valid identity evidence;
    # reject conflicting established canonical names rather than guessing by error.
    returned = tuple(call for call in invoked if call.model != call.requested_model)
    if len({call.model for call in returned}) > 1:
        raise ValueError('MODEL_EXECUTION_IDENTITY_MISMATCH')
    return ModelExecutionMetadata.model_validate(public_copy({
        'execution_mode': 'MOCK' if identity.is_mock else 'REAL',
        'provider': identity.provider, 'model': returned[-1].model if returned else identity.model,
        'source': 'PERSISTED_PLANNER_CALL', 'attempt_count': len(calls),
    }))
