import re
from app.db import models as m
from app.enrichment.acquisition import VENDORS
from app.enrichment.parsing import parse_advisory
from app.enrichment.repository import ClaimStore,emit
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome,failure

class VendorEnricher(BaseEnricher):
    name='vendor';sources=tuple(VENDORS)
    def investigate(self,ctx,session,acq):
        out=WorkOutcome();start=len(acq.checked)
        ids=list(dict.fromkeys([*ctx.aliases,*[g for r in ctx.references for g in re.findall(r'GHSA-[A-Za-z0-9-]+',r['url'])]]))[:3]
        for repo in ctx.repositories[:3]:
            key=next((k for k,v in VENDORS.items() if v==repo),None)
            if key is None:continue
            for id in ids:
                url=f'https://api.github.com/repos/{repo}/security-advisories/{id}'
                try:doc=acq.fetch(key,url,repo+':'+id,'github:'+repo.casefold())
                except Exception as exc:out.errors.append(failure(exc,key));continue
                data=parse_advisory(doc.payload,repo,ctx.canonical_id,ctx.aliases)
                if data['association']!='MATCHED':out.unresolved.append('Vendor record did not match target');continue
                ctx.vendor_documents.append({'document':doc,'parsed':data,'repository':repo})
                obs=session.get(m.SourceObservation,doc.observation_id)
                for item in data['claims']:
                    package=ctx.package(item['value'].get('package',''))
                    # A structured vendor record cannot silently change the target's package identity.
                    if item['type']!='VENDOR_CONFIRMED' and (package is None or package['ecosystem']!=item['value'].get('ecosystem')):
                        out.unresolved.append('Vendor package outside existing target scope');continue
                    subject={'package_identifier_id':package['package_id']} if package else None
                    claim=ClaimStore.add(session,ctx.target_id,item['type'],item['scope'],item['value'],subject=subject)
                    evidence=EvidenceService.add(session,claim,obs,item['value'],{'json_pointer':item['locator']},evidence_type='official_vendor_advisory')
                    out.claims.append(claim.id);out.evidence.append(evidence.id)
                    if item['type']=='FIXED_VERSION':emit(session,ctx.target_id,'FIX_VERSION_FOUND',str(claim.id),'Vendor explicitly supplied a fixed version',claim=claim,evidence=evidence,source_id=doc.source_id)
                emit(session,ctx.target_id,'VENDOR_ADVISORY_FOUND',str(doc.raw_id),'An exact-identifier official vendor advisory was found',source_id=doc.source_id,payload={'raw_document_id':str(doc.raw_id),'association':'MATCHED'})
        if out.claims:out.status='SUCCESS'
        if not ids or not ctx.repositories:out.unresolved.append('No supported official repository/advisory identifier for this target')
        return self.finish(out,acq,start)
