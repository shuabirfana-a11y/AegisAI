import pytest

@pytest.mark.parametrize('value',['nan','inf','-inf','2'])
def test_invalid_cycle_interval_is_rejected_before_any_database_or_network(value,monkeypatch):
    from app.monitoring.cli import main
    monkeypatch.delenv('AEGIS_DATABASE_URL',raising=False)
    with pytest.raises(SystemExit) as e:main(['--source','NVD','--interval',value])
    assert e.value.code==2

def test_collector_investigation_never_accepts_credentials_in_url(monkeypatch):
    from app.monitoring.cli import main
    monkeypatch.delenv('AEGIS_DATABASE_URL',raising=False)
    with pytest.raises(SystemExit) as e:main(['--source','NVD','--investigate','CVE-2099-9000001','--api-base-url','https://user:password@example.invalid'])
    assert e.value.code==2
