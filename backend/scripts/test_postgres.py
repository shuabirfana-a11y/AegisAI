"""Start/stop only this project's isolated local PostgreSQL test cluster."""
from pathlib import Path
import json, subprocess, sys
import psycopg
from psycopg import sql
ROOT=Path(__file__).resolve().parents[2]
DATA=(ROOT/'work/database_cluster').resolve()
BIN=Path(json.loads((ROOT/'work/postgresql_runtime.json').read_text())['bin'])
PORT=55435
DB='aegis_phase5_test'
URL=f'postgresql+psycopg://aegis_test@127.0.0.1:{PORT}/{DB}'

def run(name,*args):
    command=[str(BIN/(name+'.exe')),*map(str,args)]
    if name=='pg_ctl':
        # A detached Windows server may inherit pipes; wait only for pg_ctl.
        with (ROOT/'work/database_control.log').open('a',encoding='utf-8') as log:
            p=subprocess.run(command,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=60)
        if p.returncode: raise RuntimeError('pg_ctl failed; inspect work/database_control.log')
        return ''
    p=subprocess.run(command,capture_output=True,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=90)
    if p.returncode: raise RuntimeError(f'{name} failed: {p.stdout}\n{p.stderr}')
    return p.stdout

def start():
    if not DATA.is_relative_to((ROOT/'work').resolve()): raise RuntimeError('Test cluster path outside work')
    if not (DATA/'PG_VERSION').exists():
        DATA.parent.mkdir(parents=True,exist_ok=True)
        run('initdb','-D',DATA,'--username=aegis_test','--auth=trust','--encoding=UTF8','--no-locale')
    if not (DATA/'postmaster.pid').exists():
        run('pg_ctl','-D',DATA,'-l',ROOT/'work/database_cluster.log','-o',f'-h 127.0.0.1 -p {PORT} -c timezone=UTC','-w','start')
    with psycopg.connect(host='127.0.0.1',port=PORT,user='aegis_test',dbname='postgres',autocommit=True) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone():
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB)))
        version=conn.execute('SELECT version()').fetchone()[0]
    (ROOT/'work/database_test_environment.json').write_text(json.dumps({'url':URL,'database':DB,'port':PORT,'version':version,'cluster':str(DATA),'authentication':'Local test only, loopback trust; stopped after verification, never production.'},indent=2),encoding='utf-8')
    print('Isolated PostgreSQL test cluster ready at loopback port',PORT)

def stop():
    if (DATA/'postmaster.pid').exists(): run('pg_ctl','-D',DATA,'-m','fast','-w','stop')
    print('Isolated test cluster stopped')

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('start','stop'): raise SystemExit('Usage: test_postgres.py start|stop')
    start() if sys.argv[1]=='start' else stop()
