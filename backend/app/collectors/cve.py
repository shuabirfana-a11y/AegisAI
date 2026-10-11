from pathlib import Path
import json,re,subprocess
from app.collectors.base import BaseCollector,CollectionBatch,RawEnvelope
from app.normalizers import cve
from app.core.config import Settings
from app.utils.time import utcnow

REPO='https://github.com/CVEProject/cvelistV5.git'

def record_path(id):
    if not re.fullmatch(r'CVE-\d{4}-\d{4,}',id): raise ValueError('Invalid CVE path identity')
    _,year,number=id.split('-')
    return f'cves/{year}/{number[:-3]}xxx/{id}.json'

class CVECollector(BaseCollector):
    source_key='CVE_LIST'
    normalize=staticmethod(cve.normalize)

    def __init__(self,settings=None,http=None):
        self.settings=settings or Settings.from_env()
        self.http=http
        self.cache=self.settings.cve_cache.resolve()
        self.bootstrap=json.loads((Path(__file__).resolve().parents[1]/'resources/bootstrap_ids.json').read_text())['cve']

    def git(self,*args,check=True):
        hooks=self.cache.parent/'disabled-hooks';hooks.mkdir(parents=True,exist_ok=True)
        command=[self.settings.git_bin,'-c','core.autocrlf=false','-c','core.hooksPath='+str(hooks),'-C',str(self.cache),*args]
        result=subprocess.run(command,capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if check and result.returncode: raise RuntimeError('Git operation failed: '+str(result.returncode))
        return result

    def finalize_checkpoint(self,before,candidate,pending,failed):
        result=super().finalize_checkpoint(before,candidate,pending,failed)
        result['pending_paths']=[record_path(x) for x in pending]
        return result

    def collect(self,checkpoint,limit,persist_raw):
        checkpoint=checkpoint or {}
        if not (self.cache/'.git').exists():
            self.cache.parent.mkdir(parents=True,exist_ok=True)
            result=subprocess.run([self.settings.git_bin,'clone','--filter=blob:none','--depth=1','--no-checkout',REPO,str(self.cache)],capture_output=True,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if result.returncode: raise RuntimeError('CVE Git baseline acquisition failed')
        if self.git('remote','get-url','origin').stdout.decode().strip()!=REPO: raise ValueError('CVE cache origin is not official repository')
        target=self.git('ls-remote','origin','refs/heads/main').stdout.decode().split()[0]
        if not re.fullmatch('[0-9a-f]{40}',target): raise ValueError('Invalid Git commit')
        if self.git('cat-file','-e',target+'^{commit}',check=False).returncode:
            self.git('fetch','--filter=blob:none','--depth=64','origin','main')
        prefix=self.settings.cve_prefix
        if not re.fullmatch(r'cves/\d{4}/\d+xxx',prefix): raise ValueError('Invalid declared CVE scope')
        tree=self.git('ls-tree','-r','--name-only',target,'--',prefix).stdout.decode().splitlines()
        seeds=[record_path(x) for x in self.bootstrap]
        candidates=list(dict.fromkeys(seeds+[p for p in tree if re.fullmatch(r'cves/\d{4}/\d+xxx/CVE-\d{4}-\d{4,}\.json',p)]))
        covered=candidates[:limit]
        # Acquisition frontier and successful processing commit are separate during a partial batch.
        discovered=checkpoint.get('candidate_checkpoint') or checkpoint
        previous=discovered.get('commit'); prior_covered=set(discovered.get('covered_paths',[]))
        if previous and self.git('merge-base','--is-ancestor',previous,target,check=False).returncode==0:
            changed=set(self.git('diff','--name-only',previous,target,'--',*sorted(prior_covered)).stdout.decode().splitlines())
            selected=list(dict.fromkeys(sorted(changed)+[p for p in covered if p not in prior_covered]))
            rebuild=False
        else:
            selected=list(dict.fromkeys(sorted(prior_covered)+covered)); rebuild=bool(previous)
        selected=list(dict.fromkeys(checkpoint.get('pending_paths',[])+selected))
        # Same-commit bounded validation still examines exact bytes and proves downstream idempotence.
        if not selected: selected=covered
        todo=selected[:limit]
        target_cp={'commit':target,'covered_paths':sorted(prior_covered|set(covered)),'pending_paths':selected[limit:],'scope_prefix':prefix,'history_rebuilt':rebuild}
        pending=[Path(p).stem for p in selected]
        def frames():
            if todo and self.http is None: self.git('checkout',target,'--',*todo)
            for p in todo:
                url=f'https://raw.githubusercontent.com/CVEProject/cvelistV5/{target}/{p}'
                try:
                    data=self.http.get(url).content if self.http else self.git('show',target+':'+p).stdout
                    yield RawEnvelope(external_id=Path(p).stem,source_url=url,raw_payload=data,
                        metadata={'transport':'official_git_metadata_https_blob' if self.http else 'official_git','commit':target,'path':p})
                except Exception as exc:
                    yield RawEnvelope(Path(p).stem,url,b'',metadata={'fetch_error':type(exc).__name__,'commit':target,'path':p})
        return CollectionBatch(frames(),target_cp,pending,{'method':'official_git','scope_prefix':prefix,'selected_paths':len(covered),
            'initial_seed_ids':self.bootstrap,'global_complete':False,'known_gaps':['Only declared paths/limited directory baseline; not the full CVE list'],'commit':target})
