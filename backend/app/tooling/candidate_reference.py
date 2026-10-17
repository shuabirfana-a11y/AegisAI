"""Candidate addresses are identifiers for read-only source queries, not fetch authority."""
from typing import Annotated
from urllib.parse import urlsplit
from pydantic import AfterValidator, Field
from app.enrichment.rules import classify_patch
from app.enrichment.acquisition import validate_enrichment_url

def validate_candidate_reference(value):
    address=urlsplit(value)
    if address.query or address.fragment or address.username or address.password:
        raise ValueError('Candidate URL must be an exact approved patch reference')
    found=classify_patch(value,())
    if not found.get('repository') or address.netloc!='github.com':
        raise ValueError('Unsupported candidate patch reference')
    identity=address.path.rsplit('/',1)[-1]
    endpoint={'commit':'commits/','pull_request':'pulls/','release':'releases/tags/'}[found['patch_type']]
    validate_enrichment_url('https://api.github.com/repos/'+found['repository']+'/'+endpoint+identity)
    return value

CandidateReference=Annotated[str,Field(min_length=1,max_length=2000),AfterValidator(validate_candidate_reference)]
