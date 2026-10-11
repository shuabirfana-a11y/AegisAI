from packaging.version import Version,InvalidVersion
from app.enrichment.versions import intervals

def normalize_version(version,ecosystem):
    result={'raw':version,'ecosystem':ecosystem,'status':'UNKNOWN','normalized':None,'public_version':None,'reason':'No validated version strategy for this ecosystem or input'}
    if ecosystem!='PyPI' or not isinstance(version,str) or not version.strip():return result
    try:v=Version(version)
    except InvalidVersion:return result
    return {**result,'status':'NORMALIZED','normalized':str(v),'public_version':v.public,'reason':'PEP440 normalization; original retained','local_build':bool(v.local)}

def compare_version(version,value):
    n=normalize_version(version,value.get('ecosystem','unknown'))
    result={'affected':None,'normalization':n,'comparisons':[],'reason':'Version or range semantics unsupported'}
    if n['status']!='NORMALIZED':return result
    ranges=intervals(value)
    if ranges is None:return result
    # Public upstream range applies to a local build's public version; local patches cannot be inferred.
    v=Version(n['public_version']);hits=[];comparisons=[]
    for lo,li,hi,ui in ranges:
        lower=lo is None or v>lo or li and v==lo;upper=hi is None or v<hi or ui and v==hi
        hits.append(lower and upper)
        comparisons.append({'installed':str(v),'lower':str(lo) if lo else None,'lower_inclusive':li,'lower_pass':lower,
            'upper':str(hi) if hi else None,'upper_inclusive':ui,'upper_pass':upper,'in_range':lower and upper})
    return {**result,'affected':any(hits),'comparisons':comparisons,'reason':'Union of all supported intervals with exact PEP440 boundary checks'}
