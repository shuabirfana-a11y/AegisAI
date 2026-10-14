"""Export the current typed monitoring API; imports code without opening a DB."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
from export_investigation_api import identifier,typescript

def exports():
    from app.main import create_app
    full=create_app().openapi();paths={p:v for p,v in full['paths'].items() if p.startswith('/api/v1/intelligence')}
    components=full['components']['schemas'];names=set()
    def visit(value):
        if isinstance(value,dict):
            ref=value.get('$ref','')
            if ref.startswith('#/components/schemas/'):
                name=ref.rsplit('/',1)[-1]
                if name not in names:names.add(name);visit(components[name])
            for k,v in value.items():
                if k!='$ref':visit(v)
        elif isinstance(value,list):
            for v in value:visit(v)
    visit(paths)
    contract={**{k:full[k] for k in ('openapi','info')},'paths':paths,
        'components':{**{k:v for k,v in full['components'].items() if k!='schemas'},'schemas':{n:components[n] for n in sorted(names)}}}
    declaration='/** Generated from actual Pydantic/OpenAPI. ISO datetimes are strings. */\n'+''.join(
        'export type '+identifier(n)+' = '+typescript(components[n])+';\n\n' for n in sorted(names))
    declaration=declaration.rstrip()+'\n'
    result={}
    for folder in [ROOT/'docs/frontend-contracts',ROOT/'AegisAI_FRONTEND_HANDOFF_PACKAGE/api/reference']:
        result[folder/'intelligence-http.openapi.json']=json.dumps(contract,ensure_ascii=False,indent=2)+'\n'
        result[folder/'intelligence-http.d.ts']=declaration
    result[ROOT/'AegisAI_FRONTEND_HANDOFF_PACKAGE/contracts/intelligence.ts']=(ROOT/'frontend/contracts/intelligence.ts').read_text(encoding='utf-8').replace('../../docs/frontend-contracts/','../api/reference/')
    result[ROOT/'AegisAI_FRONTEND_HANDOFF_PACKAGE/contracts/poc.ts']=(ROOT/'frontend/contracts/poc.ts').read_text(encoding='utf-8').replace('../../docs/frontend-contracts/','../api/reference/')
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    values=exports()
    for path,text in values.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8')!=text:raise SystemExit('STALE_INTELLIGENCE_CONTRACT: '+str(path.relative_to(ROOT)))
        else:path.write_text(text,encoding='utf-8',newline='\n')
    contract=json.loads(values[ROOT/'docs/frontend-contracts/intelligence-http.openapi.json'])
    count=sum(method in ('get','post','put','patch','delete') for item in contract['paths'].values() for method in item)
    print(json.dumps({'status':'PASS','files':len(values),'http_operations':count,'database_connected':False}))

if __name__=='__main__':main()
