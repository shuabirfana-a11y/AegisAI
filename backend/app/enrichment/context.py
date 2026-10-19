from dataclasses import dataclass,field
from uuid import uuid4,UUID
from sqlalchemy import select
from app.db import models as m
from app.repositories.queries import latest_assessments
from app.enrichment.parsing import OFFICIAL_REPOS

@dataclass
class EnrichmentContext:
    target_id:UUID
    canonical_id:str
    aliases:list=field(default_factory=list)
    packages:list=field(default_factory=list)
    current_observation_ids:list=field(default_factory=list)
    references:list=field(default_factory=list)
    vendor_documents:list=field(default_factory=list)
    trace_id:UUID=field(default_factory=uuid4)
    task_id:UUID=field(default_factory=uuid4)

    @property
    def repositories(self):return list(dict.fromkeys(p['repository'] for p in self.packages if p.get('repository')))

    def package(self,name,ecosystem=None):
        # Legacy callers still require one unambiguous distribution, never the first name hit.
        if not isinstance(name,str):return None
        matches=[p for p in self.packages if p['name'].casefold()==name.casefold()
                 and (ecosystem is None or p['ecosystem']==ecosystem)]
        return matches[0] if len(matches)==1 else None

    def resolve_package(self,name,ecosystem,*,repository=None):
        from packaging.utils import canonicalize_name
        result={'status':'IDENTITY_UNKNOWN','original_name':name,'original_ecosystem':ecosystem,
            'normalized_name':None,'package':None,'method':'NO_SUPPORTED_IDENTITY',
            'reason':'Explicit package name and ecosystem are required','review_required':True,
            'basis_reference':None}
        if not isinstance(name,str) or not name.strip() or not ecosystem:return result
        normalized=canonicalize_name(name) if ecosystem=='PyPI' else name
        result['normalized_name']=normalized
        found=[p for p in self.packages if p['ecosystem']==ecosystem and
            (canonicalize_name(p['name']) if ecosystem=='PyPI' else p['name'])==normalized]
        if len(found)==1:
            exact=found[0]['name']==name
            return {**result,'status':'EXACT_MATCH' if exact else 'VERIFIED_ALIAS','package':found[0],
                'method':'ECOSYSTEM_PACKAGE_EXACT' if exact else 'PEP503_NAME_NORMALIZATION',
                'reason':'One exact distribution identity' if exact else 'PyPI case and separator normalization only; not a product alias',
                'review_required':False,'basis_reference':None if exact else
                'https://packaging.python.org/en/latest/specifications/name-normalization/'}
        if found:return {**result,'reason':'Multiple distribution identities require selection'}
        if any(p['name'].casefold()==name.casefold() and p['ecosystem']!=ecosystem for p in self.packages):
            return {**result,'status':'IDENTITY_CONFLICT','method':'ECOSYSTEM_MISMATCH','reason':'Same name in a different ecosystem is not the same package'}
        if repository and any(p.get('repository')==repository for p in self.packages):
            return {**result,'status':'RELATED_PACKAGE','method':'REPOSITORY_RELATION_ONLY',
                'reason':'Shared upstream repository does not establish distribution identity'}
        return {**result,'reason':'No exact supported distribution identity'}

    @classmethod
    def load(cls,session,target):
        try:id=UUID(str(target))
        except ValueError:id=None
        v=session.scalar(select(m.Vulnerability).where((m.Vulnerability.id==id)|(m.Vulnerability.canonical_id==str(target)),m.Vulnerability.deleted_at.is_(None)))
        if v is None:raise ValueError('Vulnerability not found')
        ranks=latest_assessments()
        observations=list(session.scalars(select(ranks.c.observation_id).where(ranks.c.vulnerability_id==v.id,ranks.c.rn==1)))
        aliases=list(session.scalars(select(m.ExternalIdentifier.normalized_value).join(m.VulnerabilityIdentifier,m.VulnerabilityIdentifier.identifier_id==m.ExternalIdentifier.id)
            .where(m.VulnerabilityIdentifier.vulnerability_id==v.id,m.ExternalIdentifier.identifier_type=='GHSA')))
        packages=[]
        for p in session.scalars(select(m.PackageIdentifier).join(m.AffectedVersionRange,m.AffectedVersionRange.package_identifier_id==m.PackageIdentifier.id)
            .where(m.AffectedVersionRange.vulnerability_id==v.id,m.AffectedVersionRange.observation_id.in_(observations)).distinct()):
            packages.append({'name':p.package_name,'ecosystem':p.ecosystem,'product_id':p.product_id,'package_id':p.id,
                'repository':OFFICIAL_REPOS.get(p.package_name) if p.ecosystem=='PyPI' else None})
        references=[{'url':r.url,'observation_id':str(link.observation_id)} for r,link in session.execute(
            select(m.Reference,m.VulnerabilityReference).join(m.VulnerabilityReference,m.VulnerabilityReference.reference_id==m.Reference.id)
            .where(m.VulnerabilityReference.vulnerability_id==v.id,m.VulnerabilityReference.observation_id.in_(observations)))]
        return cls(v.id,v.canonical_id,aliases,packages,observations,references)
