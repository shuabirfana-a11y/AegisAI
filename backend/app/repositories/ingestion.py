from datetime import date
import hashlib,json
from sqlalchemy import select,text
from sqlalchemy.dialects.postgresql import insert
from app.db import models as m
from app.services.identity import VulnerabilityIdentityResolver
from app.services.products import canonicalize,registry
from app.services.relevance import assess
from app.utils.time import utcnow
from app.normalizers import cve,osv,cisa_kev,ghsa,nvd

NORMALIZER_VERSIONS={'CVE_LIST':cve.VERSION,'OSV':osv.VERSION,'CISA_KEV':cisa_kev.VERSION,
    'GHSA':ghsa.VERSION,'NVD':nvd.VERSION,**{k:ghsa.VERSION for k in ('VENDOR_PYTORCH','VENDOR_VLLM','VENDOR_MLFLOW')}}
PRIORITY={'CVE_LIST':3,'OSV':2,'CISA_KEV':1,'GHSA':2,'NVD':2,'VENDOR_PYTORCH':2,'VENDOR_VLLM':2,'VENDOR_MLFLOW':2}

def unique_row(session,model,identity,values=None):
    values={**identity,**(values or {})}
    created=session.scalar(insert(model).values(**values).on_conflict_do_nothing().returning(model.id))
    if created is not None: return session.get(model,created)
    return session.scalar(select(model).where(*(getattr(model,k)==v for k,v in identity.items())))

def package_row(session,item,source):
    p=canonicalize(name=item['name'],ecosystem=item.get('ecosystem'),purl=item.get('purl'),vendor=item.get('vendor'))
    if p['ecosystem']=='unknown':
        # Unqualified names do not identify a globally shared package across publishers.
        p['canonical_key']=p['canonical_key']+':'+source.source_key
        p['package_name']=p['package_name']
        from packageurl import PackageURL
        vendor_scope=hashlib.sha256((p.get('vendor') or '<unknown-vendor>').encode()).hexdigest()[:16]
        namespace=source.source_key+':'+vendor_scope
        p['purl']=str(PackageURL(type='generic',namespace=source.source_key.lower()+'/'+vendor_scope,name=p['package_name']))
    else:namespace=''
    product=unique_row(session,m.Product,{'canonical_key':p['canonical_key']},{'canonical_name':p['canonical_name'],'vendor':p.get('vendor')})
    package=unique_row(session,m.PackageIdentifier,{'ecosystem':p['ecosystem'],'namespace':namespace,
                        'package_name':p['package_name']},{'product_id':product.id,'purl':p['purl']})
    return session.get(m.Product,package.product_id),package

def persist_record(session, source, raw, record, *, sync_run_id=None, locator=None):
    version=NORMALIZER_VERSIONS[source.source_key]
    # Serialize source content processing as well as subject identity.
    lock='record:'+source.source_key+':'+record.external_id
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,2))'),{'key':lock})
    same=session.scalar(select(m.SourceObservation).where(m.SourceObservation.source_id==source.id,
        m.SourceObservation.external_id==record.external_id,m.SourceObservation.raw_document_id==raw.id,
        m.SourceObservation.normalizer_version==version,m.SourceObservation.parse_status=='parsed').limit(1))
    if same: return {'outcome':'skipped','observation_id':same.id,'vulnerability_ids':same.details.get('vulnerability_ids',[]),'vulnerabilities_created':0}
    prior=session.scalar(select(m.SourceObservation.id).where(m.SourceObservation.source_id==source.id,
        m.SourceObservation.external_id==record.external_id,m.SourceObservation.parse_status=='parsed').limit(1))
    vulns,created=VulnerabilityIdentityResolver().resolve(session,record)
    normalized=record.model_dump(mode='json')
    observation=m.SourceObservation(source_id=source.id,raw_document_id=raw.id,sync_run_id=sync_run_id,
        external_id=record.external_id,record_type=record.record_type,retrieved_at=record.retrieved_at,http_status=200,
        raw_locator=locator or record.field_provenance.get('record',{'json_pointer':''}),
        lineage_key='|'.join(record.upstream_lineage) or source.source_key,publisher=raw.publisher,
        normalizer_version=version,normalized_payload=normalized,parse_status='parsed',
        details={'vulnerability_ids':[str(v.id) for v in vulns],'untrusted':True})
    session.add(observation);session.flush()
    for vulnerability in vulns:
        current_priority=PRIORITY.get(vulnerability.details.get('projection_source'),0)
        current_modified=vulnerability.modified_at
        newer=current_modified is None or (record.modified_at is not None and record.modified_at>=current_modified)
        if PRIORITY[source.source_key]>current_priority or (PRIORITY[source.source_key]==current_priority and newer):
            vulnerability.title=record.title or vulnerability.title
            vulnerability.description=record.description
            vulnerability.published_at=record.published_at
            vulnerability.modified_at=record.modified_at
            vulnerability.status=record.record_status
            vulnerability.details={**vulnerability.details,'projection_source':source.source_key,'projection_observation_id':str(observation.id),'unverified':True}
            if prior: vulnerability.revision+=1
        for identity in record.external_ids:
            external=unique_row(session,m.ExternalIdentifier,{'namespace':identity['namespace'],'identifier_type':identity['type'],'normalized_value':identity['value']},
                {'identifier_value':identity['value'],'source_id':source.id})
            # Each CVE owns exactly one subject; a multi-CVE advisory maps only its own CVE key to that subject.
            if identity['type']=='CVE' and identity['value']!=vulnerability.canonical_id: continue
            unique_row(session,m.VulnerabilityIdentifier,{'vulnerability_id':vulnerability.id,'identifier_id':external.id},
                {'identifier_type':identity['type'],'observation_id':observation.id})
        packages={}
        for item in record.packages or []:
            product,package=package_row(session,item,source)
            packages[(item.get('ecosystem','unknown'),item['name'])]=(product,package)
        for item in record.products or []:
            if record.packages: continue
            product,package=package_row(session,{'name':item['name'],'ecosystem':item.get('ecosystem'),'vendor':item.get('vendor')},source)
            packages[(package.ecosystem,package.package_name)]=(product,package)
        for item in record.affected_versions or []:
            key=(item['package'].get('ecosystem','unknown'),item['package']['name'])
            product,package=packages.get(key) or package_row(session,item['package'],source)
            scope=hashlib.sha256(json.dumps([str(package.id),item.get('branch'),item['locator']],sort_keys=True).encode()).hexdigest()
            session.add(m.AffectedVersionRange(vulnerability_id=vulnerability.id,product_id=product.id,package_identifier_id=package.id,
                source_id=source.id,observation_id=observation.id,scope_key=scope,
                **{k:item.get(k) for k in ['introduced','fixed','last_affected','limit_version','range_type','raw_expression','events','explicit_versions','parse_status','parse_reason','parser_version']},
                details={'locator':item['locator'],'source_version_type':item.get('source_version_type')}))
        for item in record.cvss or []:
            session.add(m.CvssAssessment(vulnerability_id=vulnerability.id,source_id=source.id,observation_id=observation.id,
                version=item['version'],vector=item.get('vector'),base_score=item['base_score'],severity=item['severity'],provider=item['provider'],
                scope_key=hashlib.sha256(item['scope_key'].encode()).hexdigest(),published_at=record.published_at,
                details={'locator':item['locator'],'score_method':item['score_method'],'unverified':True}))
        for cwe_id in record.cwe or []:
            weakness=unique_row(session,m.Weakness,{'cwe_id':cwe_id},{'name':cwe_id})
            unique_row(session,m.VulnerabilityWeakness,{'vulnerability_id':vulnerability.id,'weakness_id':weakness.id,'observation_id':observation.id})
        for item in record.references or []:
            url=item['url']
            from urllib.parse import urlsplit
            parsed=urlsplit(url)
            if parsed.scheme not in ('http','https') or not parsed.hostname: continue
            if len(url.encode())>2000: continue # preserved in raw/observation; avoids B-tree overflow, disclosed.
            reference=unique_row(session,m.Reference,{'canonical_url':url},{'url':url,'reference_type':str(item.get('type','reference')).lower()[:30],'source_id':source.id})
            unique_row(session,m.VulnerabilityReference,{'vulnerability_id':vulnerability.id,'reference_id':reference.id,'observation_id':observation.id})
        relevance=assess(record)
        session.add(m.AiRelevanceAssessment(vulnerability_id=vulnerability.id,observation_id=observation.id,
            evaluated_at=utcnow(),model_version=registry()['version'],**relevance))
        if record.exploitation:
            value=record.exploitation
            unique_row(session,m.KnownExploitation,{'vulnerability_id':vulnerability.id,'source_id':source.id,'raw_document_id':raw.id},
                {'known_exploited':value['known_exploited'],'catalog_status':value['catalog_status'],'catalog_complete':value['catalog_complete'],
                 'catalog_version':value['catalog_version'],'observed_at':record.retrieved_at,
                 'date_added':date.fromisoformat(value['date_added']) if value.get('date_added') else None,
                 'due_date':date.fromisoformat(value['due_date']) if value.get('due_date') else None,'required_action':value.get('required_action')})
    session.flush()
    return {'outcome':'updated' if prior else 'created','observation_id':observation.id,
            'vulnerability_ids':[v.id for v in vulns],'vulnerabilities_created':created}
