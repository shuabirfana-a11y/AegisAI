import re
from collections import defaultdict
from app.db import models as m
from app.enrichment.acquisition import VENDORS
from app.enrichment.parsing import parse_advisory
from app.enrichment.repository import ClaimStore,emit
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome,failure

def record_union_assertions(payload,claims):
    """Same-record, exact-package union; C2 must prove every maintenance entry.

    This creates a bound source assertion, never a trust decision or an alias.
    Original entry assertions and raw expressions remain unchanged.
    """
    from app.enrichment.version_scope import VersionScopeNormalizer
    groups=defaultdict(list)
    for item in claims:
        if item['type']=='AFFECTS_VERSION' and item['value'].get('ecosystem')=='PyPI':
            groups[item['value']['package']].append(item)
    result=[]
    for package,items in groups.items():
        if len(items)<2:continue
        value={'ecosystem':'PyPI','package':package,
               'ranges':[{'range':x['value']['range'],'parse_status':x['value']['parse_status']} for x in items]}
        locator=items[0]['locator']
        proof=VersionScopeNormalizer().normalize('AFFECTS_VERSION',value,document=payload,
            locator={'json_pointer':locator},evidence_id='pending',raw_document_id='pending',integrity_verified=True)
        if proof is None or proof.coverage!='RECORD_UNION' or len(proof.entries)!=len(items):continue
        result.append({'type':'AFFECTS_VERSION','scope':items[0]['scope'],'value':value,'locator':locator,
                       'union_member_locators':[x['locator'] for x in items]})
    return result

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
                out.unresolved.extend(data.get('unresolved',[]))
                ctx.vendor_documents.append({'document':doc,'parsed':data,'repository':repo})
                obs=session.get(m.SourceObservation,doc.observation_id)
                from app.enrichment.source_facts import persist_source_facts
                fact_claims,fact_evidence=persist_source_facts(session,ctx,obs)
                out.claims.extend(fact_claims);out.evidence.extend(fact_evidence)
                identity_evidence=[]
                for item in [*data['claims'],*record_union_assertions(doc.payload,data['claims'])]:
                    identity=ctx.resolve_package(item['value'].get('package'),item['value'].get('ecosystem'),repository=repo)
                    package=identity['package']
                    if item['type'] in ('AFFECTS_PRODUCT','AFFECTS_VERSION','FIXED_VERSION'):
                        from app.enrichment.evidence import pointer
                        identity_locator='/'.join(item['locator'].split('/')[:3])+'/package'
                        raw_package=pointer(doc.payload,identity_locator)
                        out.artifacts.setdefault('package_identity',[]).append({
                            **{k:v for k,v in identity.items() if k!='package'},'claim_type':item['type'],
                            'original_ecosystem':raw_package.get('ecosystem'),'matching_ecosystem':item['value'].get('ecosystem'),
                            'source_package':raw_package,'identity_locator':identity_locator,
                            'source_evidence_ids':list(identity_evidence),
                            'package_identifier_id':str(package['package_id']) if package else None,
                            'product_id':str(package['product_id']) if package and package.get('product_id') else None,
                            'source_id':str(doc.source_id),'raw_document_id':str(doc.raw_id),
                            'observation_id':str(obs.id),'reference':url,'locator':item['locator']})
                    # A structured vendor record cannot silently change the target's package identity.
                    if item['type'] in ('AFFECTS_PRODUCT','AFFECTS_VERSION','FIXED_VERSION') and (package is None or package['ecosystem']!=item['value'].get('ecosystem')):
                        out.unresolved.append('Vendor package outside existing target scope');continue
                    subject={'package_identifier_id':package['package_id']} if package else None
                    claim=ClaimStore.add(session,ctx.target_id,item['type'],item['scope'],item['value'],subject=subject)
                    evidence=EvidenceService.add(session,claim,obs,item['value'],{'json_pointer':item['locator']},evidence_type='official_vendor_advisory',
                        details={'normalization':'source-record-union-v1','member_locators':item['union_member_locators']}
                        if item.get('union_member_locators') else None)
                    out.claims.append(claim.id);out.evidence.append(evidence.id)
                    if item['type']=='VENDOR_CONFIRMED':identity_evidence.append(str(evidence.id))
                    if item['type']=='FIXED_VERSION':emit(session,ctx.target_id,'FIX_VERSION_FOUND',str(claim.id),'Vendor explicitly supplied a fixed version',claim=claim,evidence=evidence,source_id=doc.source_id)
                emit(session,ctx.target_id,'VENDOR_ADVISORY_FOUND',str(doc.raw_id),'An exact-identifier official vendor advisory was found',source_id=doc.source_id,payload={'raw_document_id':str(doc.raw_id),'association':'MATCHED'})
        if out.claims:out.status='SUCCESS'
        if not ids or not ctx.repositories:out.unresolved.append('No supported official repository/advisory identifier for this target')
        return self.finish(out,acq,start)
