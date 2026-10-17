"""Database lifecycle checks for derived conflicts; every fixture is synthetic."""
from datetime import timedelta
from uuid import uuid4
from hashlib import sha256
import json
import pytest
from sqlalchemy import select,func
from app.db import models as m
from app.utils.time import utcnow
from app.enrichment.repository import ClaimStore
from app.enrichment.evidence import EvidenceService
from app.enrichment.conflict import ConflictDetectionService

def material(db,seed):
    now=utcnow();v=m.Vulnerability(canonical_id='CVE-2099-'+str(uuid4().int)[:12],title='SYNTHETIC range association',status='published')
    db.add(v);db.flush()
    doc={'vulnerabilities':[
        {'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'>=2.0.0,<2.4.2','first_patched_version':'2.4.2'},
        {'package':{'ecosystem':'pip','name':'vllm'},'vulnerable_version_range':'<1.8.4','first_patched_version':'1.8.4'}]}
    cs=[ClaimStore.add(db,v.id,'FIXED_VERSION','PyPI:vllm',{'ecosystem':'PyPI','package':'vllm','version':version},
                      subject={'package_identifier_id':seed.packages[0].id}) for version in ('2.4.2','1.8.4')]
    return now,v,doc,cs

def observation(db,source,document,when,published=None):
    payload=json.dumps(document,ensure_ascii=False).encode();external='SYNTHETIC-'+uuid4().hex
    raw=m.RawDocument(source_id=source.id,external_id=external,source_url=source.base_url,published_at=published or when,retrieved_at=when,
        content_type='application/json',raw_payload=payload,content_hash=sha256(payload).hexdigest(),publisher='Synthetic',completeness='complete')
    db.add(raw);db.flush()
    obs=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,external_id=external,record_type='vulnerability',
        retrieved_at=when,lineage_key='synthetic-'+str(source.id),publisher='Synthetic',parse_status='parsed',normalizer_version='SYNTHETIC',normalized_payload={})
    db.add(obs);db.flush();return raw,obs

def test_reclassification_preserves_raw_evidence_and_historical_conflict(db,seed):
    now,v,doc,claims=material(db,seed);raw,obs=observation(db,seed.sources[0],doc,now)
    for i,c in enumerate(claims):EvidenceService.add(db,c,obs,c.value_json,{'json_pointer':f'/vulnerabilities/{i}/first_patched_version'})
    old=m.ConflictRecord(conflict_key='SYNTHETIC-'+uuid4().hex,vulnerability_id=v.id,claim_a_id=claims[0].id,claim_b_id=claims[1].id,
        scope_key='PyPI:vllm',conflict_type='FIXED_VERSION_CONFLICT',detected_at=now,status='open')
    db.add(old);db.flush()
    for i,c in enumerate(claims):EvidenceService.add(db,c,obs,claims[1-i].value_json,{'json_pointer':f'/vulnerabilities/{1-i}/first_patched_version'},
        stance='contradict',details={'conflict_id':str(old.id)})
    original=[(e.id,e.stance,e.observed_value,e.excerpt,e.excerpt_hash) for e in db.scalars(select(m.Evidence).where(m.Evidence.claim_id.in_([c.id for c in claims])))]
    payload=raw.raw_payload
    assert ConflictDetectionService.detect(db,v.id,now=now)==[]
    assert old.status=='resolved' and old.resolution['history_and_evidence_retained'] is True
    assert db.get(m.ConflictRecord,old.id) is not None
    current=[(e.id,e.stance,e.observed_value,e.excerpt,e.excerpt_hash) for e in db.scalars(select(m.Evidence).where(m.Evidence.claim_id.in_([c.id for c in claims])))]
    assert original==current and raw.raw_payload==payload

@pytest.mark.parametrize('invalid_time',['stale_retrieval','future_publication','publication_after_retrieval'])
def test_invalid_time_parallel_witness_does_not_resolve_current_conflict(db,seed,invalid_time):
    now,v,doc,claims=material(db,seed)
    raw_fresh,obs_fresh=observation(db,seed.sources[0],{'assertion':'SYNTHETIC current but no supported range entry'},now)
    when=now-timedelta(days=31) if invalid_time=='stale_retrieval' else now-timedelta(days=1) if invalid_time=='publication_after_retrieval' else now
    published=now+timedelta(days=1) if invalid_time=='future_publication' else now if invalid_time=='publication_after_retrieval' else when
    raw_old,obs_old=observation(db,seed.sources[1],doc,when,published=published)
    raw_other,obs_other=observation(db,seed.sources[2],doc,now)
    EvidenceService.add(db,claims[0],obs_fresh,claims[0].value_json,{'json_pointer':'/assertion'})
    EvidenceService.add(db,claims[0],obs_old,claims[0].value_json,{'json_pointer':'/vulnerabilities/0/first_patched_version'})
    EvidenceService.add(db,claims[1],obs_other,claims[1].value_json,{'json_pointer':'/vulnerabilities/1/first_patched_version'})
    result=ConflictDetectionService.detect(db,v.id,now=now)
    assert len(result)==1 and result[0].conflict_type=='FIXED_VERSION_CONFLICT'
    assert result[0].status=='open' and result[0].resolved_at is None
