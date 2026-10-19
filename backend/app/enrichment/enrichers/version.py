from collections import defaultdict
import os
from app.db import models as m
from app.enrichment.repository import ClaimStore,emit
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome

class VersionEnricher(BaseEnricher):
    name='version';depends_on=('vendor',);sources=('CVE_LIST','OSV','PYPI_METADATA')
    def investigate(self,ctx,session,acq):
        out=WorkOutcome()
        for oid in ctx.current_observation_ids:
            obs=session.get(m.SourceObservation,oid);data=obs.normalized_payload;groups=defaultdict(list)
            from app.enrichment.source_facts import persist_source_facts
            fact_claims,fact_evidence=persist_source_facts(session,ctx,obs)
            out.claims.extend(fact_claims);out.evidence.extend(fact_evidence)
            out.checked.append({'source':session.get(m.Source,obs.source_id).source_key,'raw_document_id':str(obs.raw_document_id),
                'checked_at':obs.retrieved_at.isoformat(),'scope':'current Phase6 normalized observation; no network'})
            for item in data.get('affected_versions') or []:
                package=item.get('package') or {};name=package.get('name') or item.get('product') or item.get('product_name')
                p=ctx.package(name or '')
                if p and p['ecosystem']=='PyPI':groups[p['name']].append(item)
            for name,items in groups.items():
                p=ctx.package(name);scope='PyPI:'+name.casefold()
                values=[{k:v for k,v in x.items() if k in ('events','range_type','explicit_versions','raw_expression','parse_status','parse_reason')} for x in items]
                value={'ecosystem':'PyPI','package':name,'ranges':values}
                claim=ClaimStore.add(session,ctx.target_id,'AFFECTS_VERSION',scope,value,subject={'package_identifier_id':p['package_id']})
                for item in items:
                    e=EvidenceService.add(session,claim,obs,value,{'json_pointer':item.get('locator','')},evidence_type='normalized_version')
                    out.evidence.append(e.id)
                out.claims.append(claim.id)
                product={'ecosystem':'PyPI','package':name}
                c=ClaimStore.add(session,ctx.target_id,'AFFECTS_PRODUCT',scope,product,subject={'package_identifier_id':p['package_id']})
                e=EvidenceService.add(session,c,obs,product,{'json_pointer':items[0].get('locator','')},evidence_type='normalized_version')
                out.claims.append(c.id);out.evidence.append(e.id)
            for item in data.get('fixed_versions') or []:
                p=ctx.package((item.get('package') or {}).get('name',''))
                if p is None or p['ecosystem']!='PyPI':continue
                value={'ecosystem':'PyPI','package':p['name'],'version':item['version']}
                c=ClaimStore.add(session,ctx.target_id,'FIXED_VERSION','PyPI:'+p['name'].casefold(),value,subject={'package_identifier_id':p['package_id']})
                e=EvidenceService.add(session,c,obs,value,{'json_pointer':item.get('locator','')},evidence_type='normalized_version')
                out.claims.append(c.id);out.evidence.append(e.id)
                emit(session,ctx.target_id,'FIX_VERSION_FOUND',str(c.id),'A source supplied an explicit fixed event',claim=c,evidence=e,source_id=obs.source_id)
        if out.claims:out.status='SUCCESS'
        else:out.unresolved.append('No supported current package version assertion')
        if os.environ.get('AEGIS_PYPI_METADATA_ENABLED')=='1':
            from app.enrichment.package_registry import attach_registry_metadata
            attach_registry_metadata(ctx,session,out,acq)
        return out
