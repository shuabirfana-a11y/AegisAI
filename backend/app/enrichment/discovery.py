"""Static discovery and association services; no repository code is executed."""
import re
from urllib.parse import quote
from app.enrichment.rules import classify_poc,classify_patch
from app.enrichment.versions import contains

class PocDiscoveryService:
    @staticmethod
    def search(acquisition,target):
        return acquisition.fetch('GITHUB','https://api.github.com/search/repositories?q='+quote(target+' in:name,description,readme')+'&per_page=5',
            'poc-search:'+target,'github:search')

class PocVerificationService:
    @staticmethod
    def verify(target,packages,repository,readme,*,independent_reference=False,affected_ranges=()):
        result=classify_poc(target,packages,repository,readme,independent_reference=independent_reference)
        versions=list(dict.fromkeys(re.findall(r'\b\d+\.\d+(?:\.\d+)?\b',readme or '')))
        matched=any(contains(r,v) is True for r in affected_ranges for v in versions)
        result['features']['affected_version_match']=matched if versions and affected_ranges else None
        if result['status']=='CONFIRMED' and not matched:
            result['status']='CANDIDATE';result['reason']='Independent citation exists but an affected-version match remains unproven'
        return result

class PatchDiscoveryService:
    @staticmethod
    def classify(url,repositories,*,explicit_advisory_reference=False):
        return classify_patch(url,repositories,explicit_advisory_reference=explicit_advisory_reference)
