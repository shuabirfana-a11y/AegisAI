"""Real gateway failures remain failures; neither missing records nor versions mean safe."""
from tests.agents.investigation.test_version_tool import invoke

def test_version_observation_missing_source_record_is_an_explicit_tool_failure(db,seed):
    got=invoke(db,seed,target='CVE-2099-9999999')
    assert got.status=='failed' and [e['code'] for e in got.errors]==['NOT_FOUND']
    assert not got.data

def test_version_observation_missing_version_is_not_a_successful_nonimpact(db,seed):
    got=invoke(db,seed,version=None)
    assert got.status=='failed' and [e['code'] for e in got.errors]==['INVALID_INPUT']
    assert not got.data
