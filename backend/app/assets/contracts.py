from uuid import UUID
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field

class ComponentInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=300)
    package_name:str|None=Field(default=None,max_length=300)
    package_identifier_id:UUID|None=None
    ecosystem:str|None=Field(default=None,max_length=40)
    namespace:str=Field(default='',max_length=200)
    purl:str|None=Field(default=None,max_length=2000)
    version:str|None=Field(default=None,max_length=200)
    source_ref:str|None=Field(default=None,max_length=1000)

class AssetInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=200)
    asset_type:Literal['service','training','application','project','server','container']='service'
    environment:Literal['production','staging','development','unknown']='unknown'
    exposure:Literal['internet','internal','development','unknown']='unknown'
    description:str|None=Field(default=None,max_length=2000)
    is_demo:bool=False

CONTENT_TRUST='UNTRUSTED_EXTERNAL_CONTENT'
