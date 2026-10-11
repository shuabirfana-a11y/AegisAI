"""Synthetic protocol fixtures, never benchmark truth or production answers."""
from uuid import uuid4

CVE = 'CVE-2099-9999001'

def task(kind='vulnerability_lookup', task_id='lookup', name='get_vulnerability',
         arguments=None, deps=()):
    return dict(type=kind, task_id=task_id, task_type='tool_sequence',
                description='SYNTHETIC protocol test',
                input_data={'steps':[{'name':name,'arguments':arguments or {'target':CVE}}]},
                dependencies=list(deps), allowed_tools=[name], max_tool_calls=1,
                acceptance_criteria=['tools_succeeded','output_nonempty'])

def valid_plan():
    return dict(plan_id=str(uuid4()), objective='SYNTHETIC vulnerability lookup',
                tasks=[task()], reasoning_summary='Query stored evidence.',confidence=0.7)

def cve_input(**kwargs):
    from app.planner.schemas import PlannerInput
    return PlannerInput(query={'question':f'{CVE}是什么？','target':CVE,
                              'request_key':str(uuid4()),**kwargs})

def context_for(target=CVE, *, input=None, policy=None):
    from app.planner.context import build_context
    from app.runtime.contracts import RuntimePolicy
    return build_context(input or cve_input(target=target), 'planner-synthetic-owner',
                         policy or RuntimePolicy(), uuid4(), uuid4())

class MemorySink:
    def __init__(self):self.records=[];self.attempts=[]
    def write(self,record):self.records.append(record)
    def record_attempt(self,context,attempt):self.attempts.append(attempt)

def gateway_with_responses(responses, *, config=None, finish_reason='stop'):
    import json
    from app.llm.config import ModelConfig
    from app.llm.gateway import ModelGateway
    from app.llm.providers.mock import MockProvider
    from app.llm.providers.base import ProviderResponse
    from app.llm.schemas import Usage
    cfg=config or ModelConfig();calls=[];sink=MemorySink()
    class SequenceMock(MockProvider):
        def generate_structured(self,request,schema):
            calls.append(request)
            value=responses[min(len(calls)-1,len(responses)-1)]
            if isinstance(value,Exception):raise value
            return ProviderResponse(value if isinstance(value,str) else json.dumps(value),self.model,
                Usage(input_tokens=2,output_tokens=3,total_tokens=5),finish_reason)
    return ModelGateway(cfg,text_provider=SequenceMock(cfg),record_sink=sink),calls,sink

def gateway_with_text(text,**kwargs):return gateway_with_responses([text],**kwargs)[0]

def structured_request():return {'messages':[{'role':'user','content':'SYNTHETIC protocol validation'}]}
