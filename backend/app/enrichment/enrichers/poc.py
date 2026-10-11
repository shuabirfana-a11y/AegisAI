import re
from urllib.parse import quote
from sqlalchemy import select
from app.db import models as m
from app.enrichment.acquisition import decode_readme
from app.enrichment.discovery import PocDiscoveryService,PocVerificationService
from app.enrichment.repository import ClaimStore,emit,ensure_review
from app.enrichment.evidence import EvidenceService
from app.enrichment.enrichers.base import BaseEnricher,WorkOutcome,failure

class PocEnricher(BaseEnricher):
    name='poc';depends_on=('vendor',);sources=('GITHUB',)
    def investigate(self,ctx,session,acq):
        out=WorkOutcome();start=len(acq.checked)
        doc=PocDiscoveryService.search(acq,ctx.canonical_id)
        payload=doc.payload
        if not isinstance(payload,dict) or not isinstance(payload.get('items'),list):raise ValueError('Invalid search response')
        if payload.get('incomplete_results'):out.status='PARTIAL';out.unresolved.append('GitHub search reported incomplete results')
        if len(payload['items'])>3:out.unresolved.append('README inspection bounded to three repositories');out.status='PARTIAL'
        out.artifacts={'search_raw_id':str(doc.raw_id),'as_of':doc.retrieved_at.isoformat(),'returned':len(payload['items']),
            'total_count':payload.get('total_count'),'inspection_limit':3,'scope':'GitHub repository search; absence is time-bounded'}
        for i,repo in enumerate(payload['items'][:3]):
            name=repo.get('full_name','')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',name) or any(x in ('.','..') for x in name.split('/')):
                out.unresolved.append('Invalid repository identity');out.status='PARTIAL';continue
            url='https://github.com/'+name
            row=session.scalar(select(m.PocCandidate).where(m.PocCandidate.vulnerability_id==ctx.target_id,m.PocCandidate.canonical_url==url))
            if row is None:
                row=m.PocCandidate(vulnerability_id=ctx.target_id,source_id=doc.source_id,observation_id=doc.observation_id,url=url,
                    canonical_url=url,repository=name,author=(repo.get('owner') or {}).get('login'),candidate_type='repository',
                    status='unknown',usability_status='not_evaluated',first_seen_at=doc.retrieved_at,last_seen_at=doc.retrieved_at)
                session.add(row);session.flush()
                emit(session,ctx.target_id,'POC_CANDIDATE_FOUND',str(row.id),'A repository search returned a static candidate',source_id=doc.source_id,payload={'candidate_id':str(row.id)})
            row.last_seen_at=doc.retrieved_at;readme=None;readme_doc=None
            try:
                readme_doc=acq.fetch('GITHUB',f'https://api.github.com/repos/{name}/readme','readme:'+name,'github:'+name.casefold())
                readme=decode_readme(readme_doc.payload)
            except Exception as exc:out.errors.append(failure(exc,'GITHUB'))
            refs=[v for v in ctx.vendor_documents if any(r.rstrip('/')==url for r in v['parsed']['references'])]
            affected=[c.value_json for c in session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==ctx.target_id,m.Claim.claim_type=='AFFECTS_VERSION'))]
            decision=PocVerificationService.verify(ctx.canonical_id,[p['name'] for p in ctx.packages],repo,readme,independent_reference=bool(refs),affected_ranges=affected)
            row.status={'CONFIRMED':'confirmed','CANDIDATE':'candidate','REJECTED':'rejected','INSUFFICIENT_EVIDENCE':'unknown'}[decision['status']]
            row.details={**decision,'verification_status':decision['status'],'search_raw_id':str(doc.raw_id),
                'readme_raw_id':str(readme_doc.raw_id) if readme_doc else None,'association_only':True}
            row.details.update({'repository_created_at':repo.get('created_at'),'repository_updated_at':repo.get('updated_at'),
                'description':repo.get('description'),'fork':repo.get('fork',False),'cve_reference':ctx.canonical_id,
                'README_reference':readme_doc.url if readme_doc else None})
            out.candidates.append(row.id)
            # The proposal has a stable identity; its current classifier decision belongs to verification.
            value={'url':url,'repository':name,'association':'candidate',
                'usability_status':'not_evaluated'}
            claim=ClaimStore.add(session,ctx.target_id,'POC_ASSOCIATION','poc:'+name.casefold(),value,subject={'poc_candidate_id':row.id})
            for legacy in session.scalars(select(m.Claim).where(m.Claim.vulnerability_id==ctx.target_id,m.Claim.claim_type=='POC_ASSOCIATION',
                m.Claim.scope_key==claim.scope_key,m.Claim.id!=claim.id)):
                human=session.scalar(select(m.VerificationResult.id).where(m.VerificationResult.claim_id==legacy.id,m.VerificationResult.verified_by_type=='human').limit(1))
                if not human:legacy.details={**legacy.details,'superseded':True,'superseded_reason':'Stable PoC proposal identity v2'};legacy.adopted=False
            obs=session.get(m.SourceObservation,(readme_doc or doc).observation_id)
            evidence=EvidenceService.add(session,claim,obs,value,{'json_pointer':'/content' if readme_doc else f'/items/{i}'},
                evidence_type='repository_readme' if readme_doc else 'repository_search',explicit=bool(readme),details={'classification':decision['status'],
                    'features':decision['features']},excerpt=readme)
            out.claims.append(claim.id);out.evidence.append(evidence.id)
            if decision['status']=='CONFIRMED':emit(session,ctx.target_id,'POC_CONFIRMED',str(row.id),'Static association confirmed; usability remains untested',claim=claim,evidence=evidence,source_id=doc.source_id)
            for ref in refs:
                e=EvidenceService.add(session,claim,session.get(m.SourceObservation,ref['document'].observation_id),value,
                    {'json_pointer':'/description','reference_url':url},evidence_type='official_vendor_advisory',details={'classification':decision['status']})
                out.evidence.append(e.id)
            if decision['status'] in ('INSUFFICIENT_EVIDENCE','CANDIDATE'):ensure_review(session,claim,'POC_UNCERTAIN',decision['reason'])
        if out.candidates and out.status!='PARTIAL':out.status='SUCCESS'
        return self.finish(out,acq,start)
