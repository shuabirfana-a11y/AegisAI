"""Server-owned receipts bind artifacts to actual allowlisted gateway outputs."""
import json,hashlib
from fastapi.encoders import jsonable_encoder

def fingerprint(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def claim_key(claim):
    return fingerprint({key:claim.get(key) for key in ('id','revision','claim_type','predicate','scope_key','value_json')})

def evidence_key(ref):return fingerprint(ref)
