"""Input-only benchmark contract. Missing context is never an inferred answer."""
from typing import Literal
from pydantic import Field
from .schema import Contract,reject_labels


class BenchmarkQuestionContract(Contract):
    category:Literal['facts','version','poc_patch','risk','multihop']
    question:str=Field(min_length=1,max_length=10000)
    target:str|None=None
    component:dict=Field(default_factory=dict)
    version:str|None=None
    owned_asset_binding:bool=False
    input_status:Literal['READY','INPUT_REQUIRED']
    missing_fields:tuple[str,...]=()

    @classmethod
    def from_input(cls,category,question,values,binding):
        reject_labels(values);reject_labels(binding)
        targets=values.get('targets')
        if targets is None:targets=[]
        if not isinstance(targets,list) or len(targets)>1:
            raise ValueError('MULTI_TARGET_SCOPE_UNSUPPORTED')
        target=values.get('target') or (targets[0] if len(targets)==1 else None)
        component=values.get('component')
        component=dict(component) if isinstance(component,dict) else {'name':component} if component else {}
        version=values.get('version',component.get('version'))
        missing=[]
        if not target:missing.append('target')
        needs_asset=category in ('version','risk') or (category=='multihop' and bool(component or binding.get('asset_id')))
        if needs_asset:
            if not component:missing.append('component')
            if not version:missing.append('version')
            for field in ('asset_id','component_id'):
                if not binding.get(field):missing.append(field)
        return cls(category=category,question=question,target=target,component=component,version=version,
                   owned_asset_binding=bool(binding.get('asset_id') and binding.get('component_id')),
                   input_status='INPUT_REQUIRED' if missing else 'READY',missing_fields=tuple(missing))
