from sqlalchemy import select
from app.db import models as m
from app.enrichment.discovery import PatchDiscoveryService
from app.enrichment.repository import ClaimStore,emit
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome,failure

class PatchEnricher(BaseEnricher):
    name='patch';depends_on=('vendor',);sources=('GITHUB',)
    def investigate(self,ctx,session,acq):
        out=WorkOutcome();start=len(acq.checked);links={}
        for vendor in ctx.vendor_documents:
            for url in vendor['parsed']['references']:links[url]=vendor
        for ref in ctx.references:links.setdefault(ref['url'],None)
        checked_count=0
        for url,vendor in links.items():
            data=PatchDiscoveryService.classify(url,ctx.repositories,explicit_advisory_reference=vendor is not None)
            if data['status']=='INSUFFICIENT_EVIDENCE' or not data['official']:continue
            package=next((p for p in ctx.packages if p.get('repository','').casefold()==data['repository'].casefold()),None)
            if package is None:continue
            if checked_count>=5:out.unresolved.append('Patch scope capped at five checked references');break
            checked_count+=1
            path={'commit':'commits/','pull_request':'pulls/','release':'releases/tags/'}[data['patch_type']]
            identity=url.rsplit('/',1)[-1]
            try:doc=acq.fetch('GITHUB','https://api.github.com/repos/'+data['repository']+'/'+path+identity,
                'patch:'+url,'github:'+data['repository'].casefold())
            except Exception as exc:out.errors.append(failure(exc,'GITHUB'));continue
            if data['patch_type']=='commit' and doc.payload.get('sha')!=data['commit_sha']:raise ValueError('Commit response mismatches full SHA')
            if data['patch_type']=='pull_request' and str(doc.payload.get('number'))!=identity:raise ValueError('Pull response mismatches number')
            if data['patch_type']=='release' and doc.payload.get('tag_name')!=identity:raise ValueError('Release response mismatches tag')
            row=session.scalar(select(m.PatchCandidate).where(m.PatchCandidate.vulnerability_id==ctx.target_id,
                m.PatchCandidate.product_id==package['product_id'],m.PatchCandidate.branch=='',m.PatchCandidate.patch_type==data['patch_type'],m.PatchCandidate.identity_key==url))
            if row is None:
                row=m.PatchCandidate(vulnerability_id=ctx.target_id,product_id=package['product_id'],source_id=doc.source_id,
                    observation_id=doc.observation_id,patch_type=data['patch_type'],identity_key=url,url=url,
                    commit_sha=data['commit_sha'],release_version=data['release_version'],status=data['status'].lower(),first_seen_at=doc.retrieved_at,
                    details={'association_reason':data['reason'],'association_only':True,'no_patch_execution':True})
                session.add(row);session.flush()
                emit(session,ctx.target_id,'PATCH_FOUND',str(row.id),'A patch reference was checked against official repository metadata',source_id=doc.source_id,payload={'candidate_id':str(row.id)})
            row.status=data['status'].lower();row.observation_id=doc.observation_id
            row.details={**row.details,'association_reason':data['reason'],'association_only':True,'no_patch_execution':True,'last_checked_at':doc.retrieved_at.isoformat()}
            kind='FIX_COMMIT' if data['patch_type']=='commit' else 'PATCH_EXISTS'
            value={'url':url,'repository':data['repository'],'patch_type':data['patch_type'],'commit_sha':data['commit_sha'],
                'release_version':data['release_version'],'association':data['status']}
            claim=ClaimStore.add(session,ctx.target_id,kind,'patch:'+url,value,subject={'patch_candidate_id':row.id})
            evidence_doc=vendor['document'] if vendor else doc
            e=EvidenceService.add(session,claim,session.get(m.SourceObservation,evidence_doc.observation_id),value,
                {'json_pointer':'/description' if vendor else '/html_url','reference_url':url},
                evidence_type='official_patch' if vendor else 'repository_metadata',explicit=vendor is not None)
            out.claims.append(claim.id);out.evidence.append(e.id);out.candidates.append(row.id)
        if out.candidates:out.status='SUCCESS'
        return self.finish(out,acq,start)
