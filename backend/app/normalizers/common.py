import re
from cvss import CVSS2,CVSS3,CVSS4

CVE_RE=re.compile(r'^CVE-\d{4}-\d{4,}$')

def external(value,namespace='global'):
    typ='CVE' if CVE_RE.fullmatch(value) else 'GHSA' if value.startswith('GHSA-') else 'OSV'
    return {'namespace':namespace,'type':typ,'value':value}

def metric(vector,*,provider,locator,explicit_score=None,version=None,severity=None):
    version=version or ('4.0' if vector.startswith('CVSS:4.0/') else '3.1' if vector.startswith('CVSS:3.1/') else '3.0' if vector.startswith('CVSS:3.0/') else '2.0')
    if explicit_score is None:
        calculator={'2.0':CVSS2,'3.0':CVSS3,'3.1':CVSS3,'4.0':CVSS4}[version](vector)
        score=float(calculator.scores()[0]); severity=calculator.severities()[0].lower(); method='computed_from_source_vector'
    else: score=float(explicit_score); method='source_explicit'
    severity=(severity or 'unknown').lower()
    if severity=='none': severity='info'
    return {'version':version,'vector':vector,'base_score':score,'severity':severity,'provider':provider,
            'scope_key':provider+':CVSS:'+version+':base','locator':locator,'score_method':method}
