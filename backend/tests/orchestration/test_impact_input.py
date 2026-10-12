"""Input projection must retain already parsed source facts, never guess ranges."""
import importlib
from types import SimpleNamespace


def test_parsed_range_retains_events_for_existing_comparator():
    module=importlib.import_module('app.agents.verification.asset_snapshot')
    project=getattr(module,'candidate_version_value',None)
    assert callable(project), 'Missing structured source range adapter'
    item={'raw_expression':'{"events":[{"introduced":"0"},{"fixed":"0.7.0"}]}',
          'events':[{'introduced':'0'},{'fixed':'0.7.0'}],'range_type':'ECOSYSTEM','parse_status':'parsed'}
    claim=SimpleNamespace(value={'ecosystem':'PyPI','package':'vllm'})
    result=project(item,claim)
    from app.enrichment.versions import contains
    assert contains(result,'0.6.0') is True
    assert contains(result,'0.7.0') is False


def test_unsupported_range_stays_unsupported():
    module=importlib.import_module('app.agents.verification.asset_snapshot')
    project=getattr(module,'candidate_version_value',None)
    assert callable(project), 'Missing structured source range adapter'
    value=project({'raw_expression':'any potentially vulnerable version','parse_status':'unsupported'},
        SimpleNamespace(value={'ecosystem':'PyPI','package':'vllm'}))
    from app.enrichment.versions import contains
    assert contains(value,'0.6.0') is None
