"""Question text can supply literal context, never ground-truth values."""
from uuid import uuid4
import pytest
from evaluation.bench.schema import Question
from evaluation.bench.http_investigation import build_request


def test_natural_text_is_normalized_into_existing_investigation_request():
    q=Question(id='synthetic-input-only',category='version',question='我的 vLLM 0.6.0 是否受 CVE-2099-9999001 影响？',
        origin='TEST_FIXTURE',source_ids=['synthetic-source'],input_context={})
    body=build_request(q,{'asset_id':str(uuid4()),'component_id':str(uuid4())})
    assert body['asset_scope']['target']=='CVE-2099-9999001'
    assert body['asset_scope']['component']['version']=='0.6.0'
    assert body['user_query']==q.question


def test_unknown_version_is_not_guessed_by_question_adapter():
    q=Question(id='synthetic-input-only',category='version',question='vLLM 是否受 CVE-2099-9999001 影响？',
        origin='TEST_FIXTURE',source_ids=['synthetic-source'],input_context={})
    body=build_request(q,{'asset_id':str(uuid4()),'component_id':str(uuid4())})
    assert body['asset_scope']['component']['name']=='vllm'
    assert 'version' not in body['asset_scope']['component']
