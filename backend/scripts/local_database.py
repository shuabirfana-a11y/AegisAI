"""Own loopback development database; never modifies the Phase5 test database."""
from pathlib import Path
import json,subprocess,sys
import psycopg
from psycopg import sql

ROOT=Path(__file__).resolve().parents[2]
DATA=(ROOT/'work/phase6_cluster').resolve()
BIN=Path(json.loads((ROOT/'work/postgresql_runtime.json').read_text())['bin'])
DB='aegis_phase6'
PORT=55436
URL=f'postgresql+psycopg://aegis_local@127.0.0.1:{PORT}/{DB}'

def run(name,*args):
    with (ROOT/'work/phase6_database_control.log').open('a',encoding='utf-8') as log:
        result=subprocess.run([str(BIN/(name+'.exe')),*map(str,args)],stdout=log,stderr=log,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),timeout=60)
    if result.returncode:raise RuntimeError('Development database operation failed; see control log')

def main(action):
    if not DATA.is_relative_to((ROOT/'work').resolve()):raise RuntimeError('Invalid owned development cluster path')
    if action=='stop':
        if (DATA/'postmaster.pid').exists():run('pg_ctl','-D',DATA,'-m','fast','-w','stop')
        print('Development cluster stopped');return
    if not (DATA/'PG_VERSION').exists():run('initdb','-D',DATA,'--username=aegis_local','--auth=trust','--encoding=UTF8','--no-locale')
    if not (DATA/'postmaster.pid').exists():run('pg_ctl','-D',DATA,'-l',ROOT/'work/phase6_database.log','-o',f'-h 127.0.0.1 -p {PORT} -c timezone=UTC','-w','start')
    with psycopg.connect(host='127.0.0.1',port=PORT,user='aegis_local',dbname='postgres',autocommit=True) as conn:
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(DB,)).fetchone():conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DB)))
        version=conn.execute('SELECT version()').fetchone()[0]
    (ROOT/'work/phase6_database_environment.json').write_text(json.dumps({'database_url':URL,'database':DB,'port':PORT,'version':version,
        'kind':'LOCAL DEVELOPMENT; REAL SOURCE DATA; LOOPBACK TRUST ONLY; NO WINDOWS SERVICE','cluster':str(DATA)},indent=2),encoding='utf-8')
    print('Local development database ready on loopback port',PORT)

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('start','stop'):raise SystemExit('Choose start or stop')
    main(sys.argv[1])
