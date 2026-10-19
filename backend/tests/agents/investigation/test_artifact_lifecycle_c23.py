"""A complete observed version is deliverable, never a verified safety verdict."""
from copy import deepcopy
from uuid import uuid4
import pytest
from app.agents.investigation.normalize import normalize_investigation
from tests.agents.investigation.helpers import execution,source,CVE


def observation():
    return {'canonical_id':CVE,'vulnerability_id':str(uuid4()),
        'component':{'name':'synthetic-lib','ecosystem':'PyPI','version':'4.1'},
        'identity_resolution':{'status':'RESOLVED'},
        'source_range_results':[{'source_id':str(uuid4()),'is_current':True,
            'range_result':'OUT_OF_RANGE','verified':False}], 'uncertainties':[]}


def observed(data=None,refs=None,status='success'):
    data=observation() if data is None else data
    item,ctx,out=execution(data=data,refs=refs if refs is not None else [source()],
        names=['inspect_component_version'],statuses=[status])
    args={'target':CVE,'name':'synthetic-lib','ecosystem':'PyPI','version':'4.1'}
    item=item.model_copy(update={'input_data':{'steps':[{'name':'inspect_component_version','arguments':args}]}})
    out=out.model_copy(update={'receipts':(out.receipts[0].model_copy(update={'arguments':args}),)})
    return item,ctx,out


def test_standalone_version_observation_is_complete_but_not_confirmed():
    item,ctx,out=observed();before=out.model_dump(mode='json')
    got=normalize_investigation(item,out)
    assert got.status=='COMPLETE' and got.information_status=='CANDIDATE'
    assert got.runtime_status=='SUCCESS' and got.artifact_id==out.artifact.artifact_id
    assert got.version_match==out.receipts[0].envelope.data
    assert got.evidence==out.artifact.evidence and out.model_dump(mode='json')==before
    assert not any(ref.get('verified') for ref in got.evidence)


@pytest.mark.parametrize('missing',['canonical_id','vulnerability_id','component','source_range_results','identity_resolution'])
def test_incomplete_version_observation_stays_uncertain(missing):
    data=observation();data.pop(missing);item,ctx,out=observed(data)
    got=normalize_investigation(item,out)
    assert got.status=='INSUFFICIENT_EVIDENCE' and got.information_status=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('change',[{'authority_level':'community'},{'is_current':False},{'locator':None}])
def test_observation_does_not_bypass_existing_source_requirements(change):
    item,ctx,out=observed(refs=[source(**change)])
    assert normalize_investigation(item,out).status=='INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('field,value',[('canonical_id','CVE-2099-0000002'),('version','9.9'),('name','other-lib')])
def test_wrong_target_or_component_cannot_be_delivered_as_complete(field,value):
    data=observation()
    if field=='canonical_id':data[field]=value
    else:data['component'][field]=value
    item,ctx,out=observed(data)
    assert normalize_investigation(item,out).status!='COMPLETE'


def test_no_result_or_failed_observation_cannot_become_success():
    for state in ('failed','no_result'):
        item,ctx,out=observed({},status=state)
        got=normalize_investigation(item,out)
        assert got.status!='COMPLETE' and got.information_status!='CONFIRMED'


def test_unknown_identity_and_range_remain_uncertain():
    data=observation();data['identity_resolution']['status']='UNKNOWN'
    data['source_range_results']=[];item,ctx,out=observed(data)
    assert normalize_investigation(item,out).status=='INSUFFICIENT_EVIDENCE'


def test_conflicting_source_claims_remain_conflicting():
    from tests.agents.investigation.test_normalize import confirmed_claim
    a,ar=confirmed_claim();b,br=confirmed_claim();b['value_json']={'raw_expression':'>=0.5,<0.8'}
    data=observation();data['intelligence']={'claims':[a,b]}
    item,ctx,out=observed(data,refs=[ar,br]);got=normalize_investigation(item,out)
    assert got.status=='CONFLICT' and got.conflicts


@pytest.fixture
def lifecycle_seed(engine):
    # New source history only: both the range and its evidence reference the
    # current immutable observation, unlike the older fixture's historical ref.
    from sqlalchemy import select
    from hashlib import sha256
    from app.db import models as m
    from app.db.session import transaction
    from tests.agents.investigation.conftest import investigation_seed
    from app.utils.time import utcnow
    seed=investigation_seed.__wrapped__(engine)
    with transaction(engine) as db:
        obs=db.get(m.SourceObservation,seed.observation_id)
        version=db.scalar(select(m.AffectedVersionRange).where(m.AffectedVersionRange.observation_id==obs.id))
        value={'ecosystem':'PyPI','package':seed.component['package_name'],'raw_expression':version.raw_expression}
        claim=m.Claim(claim_key='c23-lifecycle:'+uuid4().hex,vulnerability_id=seed.vulnerability_id,
            package_identifier_id=version.package_identifier_id,
            claim_type='AFFECTS_VERSION',predicate='AFFECTS_VERSION',scope_key=version.scope_key,value_json=value)
        db.add(claim);db.flush();text='SYNTHETIC lifecycle range '+version.raw_expression
        db.add(m.Evidence(claim_id=claim.id,source_id=obs.source_id,raw_document_id=obs.raw_document_id,
            observation_id=obs.id,scope_key=claim.scope_key,evidence_type='source_excerpt',stance='support',
            excerpt=text,excerpt_hash=sha256(text.encode()).hexdigest(),
            source_url=db.get(m.RawDocument,obs.raw_document_id).source_url,
            retrieved_at=utcnow(),locator={'json_pointer':'/synthetic/range'},locator_key='c23-range',
            observed_value=value,publisher='SYNTHETIC',lineage_key=obs.lineage_key))
    return seed


def run_split(engine,seed):
    from app.agents.investigation.service import IntelligenceInvestigationService
    from app.planner.schemas import PlannerInput
    from tests.planner.fixtures import cve_input,gateway_with_responses,task
    from tests.agents.investigation.test_end_to_end import plan_for
    p=plan_for(seed);p['tasks'].append(task('vulnerability_lookup','version',
        'inspect_component_version',{'target':seed.cve,**seed.component}))
    gw,calls,sink=gateway_with_responses([p]);svc=IntelligenceInvestigationService(engine,gw)
    inp=PlannerInput(query=cve_input(target=seed.cve).query,component=seed.component)
    try:saved=svc.plan_and_run(inp,seed.actor)
    finally:gw.close()
    return svc,saved,inp


def test_real_tool_persistence_and_reader_deliver_same_version_artifact(engine,lifecycle_seed):
    from app.db import models as m
    from app.db.session import transaction
    svc,saved,inp=run_split(engine,lifecycle_seed)
    assert saved.runtime_status=='COMPLETED'
    first=svc.read_results(saved.runtime_run_id,lifecycle_seed.actor)
    got=next(a for a in first.artifacts if a.task_id=='version')
    assert got.status=='COMPLETE' and got.runtime_status=='SUCCESS'
    assert got.information_status!='CONFIRMED'
    with transaction(engine) as db:
        ns=db.get(m.AgentRun,saved.runtime_run_id).details['runtime_v1']
        assert str(got.artifact_id)==ns['artifacts']['version']['artifact_id']==ns['traces']['version']['artifact_id']
        assert ns['traces']['version']['status']==ns['artifacts']['version']['status']=='SUCCESS'
    assert svc.read_results(saved.runtime_run_id,lifecycle_seed.actor)==first
    with pytest.raises(LookupError):svc.read_results(saved.runtime_run_id,'different-owner')


@pytest.mark.parametrize('mutation',['run_id','artifact_id','type'])
def test_reader_rejects_wrong_run_id_artifact_id_or_type(engine,lifecycle_seed,mutation):
    from app.db import models as m
    from app.db.session import transaction
    svc,saved,inp=run_split(engine,lifecycle_seed)
    with transaction(engine) as db:
        row=db.get(m.AgentRun,saved.runtime_run_id);original=deepcopy(row.details);edited=deepcopy(original)
        art=edited['runtime_v1']['artifacts']['version']
        if mutation=='type':art['schema_version']='unregistered-artifact-type'
        else:art[mutation]=str(uuid4())
        row.details=edited
    try:
        with pytest.raises((ValueError,RuntimeError)):svc.read_results(saved.runtime_run_id,lifecycle_seed.actor)
    finally:
        with transaction(engine) as db:db.get(m.AgentRun,saved.runtime_run_id).details=original
