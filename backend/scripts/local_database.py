"""Own loopback development database; never modifies the Phase5 test database."""
from pathlib import Path
import json,subprocess,sys
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[2]
DATA=(ROOT/'work/phase6_cluster').resolve()
DB='aegis_phase6'
PORT=55436
URL=f'postgresql+psycopg://aegis_local@127.0.0.1:{PORT}/{DB}'

def run(name,*args,accepted=(0,),timeout=60):
    binary=Path(json.loads((ROOT/'work/postgresql_runtime.json').read_text())['bin'])
    with (ROOT/'work/phase6_database_control.log').open('a',encoding='utf-8') as log:
        result=subprocess.run([str(binary/(name+'.exe')),*map(str,args)],stdout=log,stderr=log,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=timeout)
    if result.returncode not in accepted:raise RuntimeError('Development database operation failed; see control log')
    return result.returncode

def server_running():
    # A PID file may survive a machine restart; pg_ctl checks the actual server.
    return run('pg_ctl','-D',DATA,'status',accepted=(0,3),timeout=10)==0

def main(action):
    if not DATA.is_relative_to((ROOT/'work').resolve()):raise RuntimeError('Invalid owned development cluster path')
    if action=='stop':
        if (DATA/'PG_VERSION').exists() and server_running():run('pg_ctl','-D',DATA,'-m','fast','-w','stop')
        print('Development cluster stopped');return
    if not (DATA/'PG_VERSION').exists():run('initdb','-D',DATA,'--username=aegis_local','--auth=trust','--encoding=UTF8','--no-locale')
    if not server_running():run('pg_ctl','-D',DATA,'-l',ROOT/'work/phase6_database.log','-o',f'-h 127.0.0.1 -p {PORT} -c timezone=UTC','-w','-t','30','start',timeout=40)
    with psycopg.connect(host='127.0.0.1',port=PORT,user='aegis_local',dbname='postgres',autocommit=True,connect_timeout=5) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone():conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB)))
        version=conn.execute('SELECT version()').fetchone()[0]
    (ROOT/'work/phase6_database_environment.json').write_text(json.dumps({'database_url':URL,'database':DB,'port':PORT,'version':version,
        'kind':'LOCAL DEVELOPMENT; REAL SOURCE DATA; LOOPBACK TRUST ONLY; NO WINDOWS SERVICE','cluster':str(DATA)},indent=2),encoding='utf-8')
    print('Local development database ready on loopback port',PORT)

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('start','stop'):raise SystemExit('Choose start or stop')
    main(sys.argv[1])
