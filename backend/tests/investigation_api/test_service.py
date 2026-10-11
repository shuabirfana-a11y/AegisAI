from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.investigation_api.service import InvestigationApiService
from app.investigation_api.errors import ApiFailure


def test_terminal_without_gate_is_unavailable_not_retry_forever():
    service = object.__new__(InvestigationApiService)
    service.reader = SimpleNamespace(get_result=lambda *args, **kwargs: SimpleNamespace(
        context=SimpleNamespace(current_stage='FAILED', integration_result_id=None)))
    with pytest.raises(ApiFailure) as caught:
        service.integration(uuid4(), actor='SYNTHETIC-owner')
    assert caught.value.code == 'RESULT_UNAVAILABLE'
    assert caught.value.retryable is False
