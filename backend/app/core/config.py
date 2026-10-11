from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class Settings:
    database_url: str | None=field(default=None,repr=False)
    http_timeout: float=30
    retries: int=3
    max_bytes: int=16777216
    request_interval: float=0.1
    user_agent: str='AegisAI/0.1 (bounded academic ingestion)'
    git_bin: str=str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe')
    cve_cache: Path=Path(__file__).resolve().parents[3]/'work/ingestion/cvelistV5'
    cve_prefix: str='cves/2025/32xxx'
    task_timeout: int=600

    @classmethod
    def from_env(cls):
        settings=cls(database_url=os.environ.get('AEGIS_DATABASE_URL'),
            http_timeout=float(os.environ.get('AEGIS_HTTP_TIMEOUT','30')),
            retries=int(os.environ.get('AEGIS_HTTP_RETRIES','3')),
            request_interval=float(os.environ.get('AEGIS_REQUEST_INTERVAL','0.1')),
            user_agent=os.environ.get('AEGIS_USER_AGENT',cls.user_agent),
            git_bin=os.environ.get('AEGIS_GIT_BIN',cls.git_bin),
            cve_cache=Path(os.environ.get('AEGIS_CVE_CACHE',str(cls.cve_cache))),
            cve_prefix=os.environ.get('AEGIS_CVE_PREFIX',cls.cve_prefix))
        if settings.http_timeout<=0 or not 0<=settings.retries<=5 or settings.request_interval<0:
            raise ValueError('Invalid bounded HTTP settings')
        return settings
