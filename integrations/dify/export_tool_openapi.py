"""Export live backend tool contracts as Dify-importable OpenAPI 3.0.

The secret stays in the process environment, never in the exported schema.
Run after the Phase 9 protected contract endpoint is available.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from urllib import request

ENVELOPE = {
    'type':'object',
    'required':['tool','status','data','evidence_refs','warnings','errors','retryable','trace_id','duration_ms'],
    'properties':{
        'tool':{'type':'string'},'status':{'type':'string','enum':['success','partial','no_result','failed']},
        'data':{'description':'Structured data; shape depends on the individual tool.'},
        'evidence_refs':{'type':'array','items':{'type':'object','additionalProperties':True}},
        'warnings':{'type':'array','items':{'type':'string'}},
        'errors':{'type':'array','items':{'type':'object','additionalProperties':True}},
        'retryable':{'type':'boolean'},'trace_id':{'type':'string'},'duration_ms':{'type':'integer','minimum':0}
    }
}

def openapi30_schema(value):
    """Translate current Pydantic nullable/const schema syntax to OpenAPI 3.0."""
    if isinstance(value,list):
        return [openapi30_schema(item) for item in value]
    if not isinstance(value,dict):
        return value
    if '$defs' in value:
        raise ValueError('Referenced input definitions require an explicit component mapping before export.')
    result={key:openapi30_schema(item) for key,item in value.items()}
    if 'const' in result:
        result['enum']=[result.pop('const')]
    if 'anyOf' in result and any(item.get('type')=='null' for item in result['anyOf']):
        alternatives=[item for item in result.pop('anyOf') if item.get('type')!='null']
        if len(alternatives)==1:
            result.update(alternatives[0])
        else:
            result['anyOf']=alternatives
        result['nullable']=True
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'tool-gateway.openapi.json')
    parser.add_argument('--contracts-file',type=Path,help='Offline snapshot of actual backend contracts; does not claim a live HTTP export.')
    options=parser.parse_args()
    token=os.environ.get('AEGIS_ASSET_TOKEN','')
    if options.contracts_file:
        payload=json.loads(options.contracts_file.read_text(encoding='utf-8'))
        provenance='ACTUAL_BACKEND_SCHEMA_OFFLINE_SNAPSHOT'
    else:
        if not token:
            parser.error('AEGIS_ASSET_TOKEN must be configured privately in the environment')
        # The backend address is fixed by deployment. No caller-supplied URL exists.
        req=request.Request('http://127.0.0.1:8000/api/v1/tools/contracts',headers={'Authorization':'Bearer '+token})
        with request.urlopen(req,timeout=15) as response:
            payload=json.loads(response.read(1_000_000))
        provenance='EXPORTED_FROM_LIVE_BACKEND_CONTRACTS'
    # Accept only the documented root structure; do not invent missing schemas.
    contracts=payload.get('tools') if isinstance(payload,dict) else None
    if not isinstance(contracts,list) or not contracts:
        raise ValueError('Unexpected tool contracts response: expected nonempty tools array.')
    paths={}
    for contract in contracts:
        name=contract.get('name') or contract.get('tool')
        input_schema=contract.get('input_schema')
        if not isinstance(name,str) or not name.replace('_','').isalnum() or not isinstance(input_schema,dict):
            raise ValueError('A tool contract lacks a valid name/input_schema.')
        if contract.get('permission') not in ('READ_ONLY',):
            continue
        paths['/api/v1/tools/'+name]={'post':{
            'operationId':name,'description':contract.get('description','AegisAI READ_ONLY structured tool'),
            'requestBody':{'required':True,'content':{'application/json':{'schema':openapi30_schema(input_schema)}}},
            'responses':{'200':{'description':'Auditable ToolEnvelope','content':{'application/json':{'schema':{'$ref':'#/components/schemas/ToolEnvelope'}}}},
                         '401':{'description':'Backend credential missing or invalid'},'422':{'description':'Input failed validation'}},
            'security':[{'AegisBearer':[]}]}}
    if not paths:
        raise ValueError('No READ_ONLY structured tools were exported.')
    document={'openapi':'3.0.3','info':{'title':'AegisAI Agent Safe Tool Gateway','version':'phase9.v1'},
        'servers':[{'url':'http://aegis_gateway:8080'}],'paths':paths,
        'components':{'schemas':{'ToolEnvelope':ENVELOPE},'securitySchemes':{'AegisBearer':{'type':'http','scheme':'bearer'}}},
        'x-aegis-exported-at':datetime.now(timezone.utc).isoformat(),'x-aegis-contract-provenance':provenance}
    if token and token in json.dumps(document):
        raise ValueError('Refusing to export a schema containing the configured secret.')
    options.output.write_text(json.dumps(document,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':provenance,'tools':len(paths),'output':str(options.output)}))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
