"""Explainable static association and evidence rules, with explicit abstention."""
import re
from datetime import timedelta
from urllib.parse import urlsplit
from app.enrichment.contracts import CONTENT_TRUST
from app.enrichment.versions import canonical_value,intervals,contains

def classify_poc(target,packages,repository,readme,*,independent_reference=False):
    text=(readme or '').casefold()
    references={x.upper() for x in re.findall(r'CVE-\d{4}-\d{4,}|GHSA-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}',readme or '',re.I)}
    f={'identifier':target.upper() in references,'product':any(re.search(r'(?<![\w-])'+re.escape(p.casefold())+r'(?![\w-])',text) for p in packages),
        'mechanism':bool(re.search(r'remote code execution|deseriali[sz]|sql injection|path traversal|ssrf|denial of service|buffer overflow|memory exhaustion|decompression|arbitrary code',text)),
        'reproduction':bool(re.search(r'proof.of.concept|steps to reproduce|reproduc(?:e|tion)|\bpoc\b',text)),
        'scanner_or_list':bool(re.search(r'\bscanner\b|detect only|vulnerability (?:list|database)|curated (?:cve|vulnerability)|not a (?:poc|proof)',text)),
        'fork':bool(repository.get('fork')),'independent_reference':bool(independent_reference),
        'mentions_version':bool(re.search(r'\b\d+\.\d+(?:\.\d+)?\b',text))}
    if f['scanner_or_list'] or references and not f['identifier']:
        status='REJECTED';reason='Scanner/list or explicit different identifier; not an exploit association.'
    elif all(f[k] for k in ['identifier','product','mechanism','reproduction']):
        status='CONFIRMED' if independent_reference and not f['fork'] else 'CANDIDATE'
        reason='Exact identifier/product/mechanism/reproduction; independent explicit reference required for confirmation.'
    else:status='INSUFFICIENT_EVIDENCE';reason='Missing explicit identifier, product, mechanism or reproduction evidence.'
    return {'status':status,'features':f,'reason':reason,'abstention_reason':reason if status=='INSUFFICIENT_EVIDENCE' else None,
        'usability_status':'not_evaluated','content_trust_level':CONTENT_TRUST}

def classify_patch(url,official_repos,*,explicit_advisory_reference=False,message=''):
    parsed=urlsplit(url);match=re.fullmatch(r'/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(commit|pull|releases/tag)/([^/?#]+)',parsed.path)
    result={'status':'INSUFFICIENT_EVIDENCE','reason':'Unrecognized or unapproved patch reference','url':url}
    if parsed.scheme!='https' or parsed.netloc!='github.com' or not match:return result
    repo,kind,id=match.groups();official=repo.casefold() in {r.casefold() for r in official_repos}
    if kind=='commit' and not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',id):return result
    if kind=='pull' and not id.isdecimal():return result
    result.update({'repository':repo,'patch_type':{'commit':'commit','pull':'pull_request','releases/tag':'release'}[kind],
        'commit_sha':id if kind=='commit' else None,'release_version':id if kind=='releases/tag' else None,
        'status':'CONFIRMED' if official and explicit_advisory_reference else 'CANDIDATE',
        'reason':'Explicit official advisory reference' if official and explicit_advisory_reference else 'Reference needs explicit official linkage',
        'official':official})
    return result

def evaluate_claim(kind,value,evidence,now):
    current=[]
    for item in evidence:
        acquired=item.get('retrieved_at')
        if not item.get('is_current',True) or acquired is None or acquired.tzinfo is None:continue
        if acquired>now+timedelta(minutes=5) or acquired<now-timedelta(days=30):continue
        current.append(item)
    supports=[x for x in current if x.get('stance')=='support' and canonical_value(kind,x.get('value') or {})==canonical_value(kind,value)]
    contradicts=[x for x in current if x.get('stance')=='contradict' and x.get('explicit',False)]
    groups=sorted({x.get('lineage') or 'unresolved-origin' for x in supports if x.get('explicit') and x.get('authority') in ('official','authoritative')})
    status='INSUFFICIENT_EVIDENCE';reason='Insufficient current, explicit, independent evidence.'
    explicit_official=any(x.get('explicit') and x.get('authority') in ('official','authoritative') and
        x.get('evidence_type') in ('official_vendor_advisory','official_patch','kev_record') for x in supports)
    if kind=='FIXED_VERSION' and not value.get('version'):reason='No explicit normalized fixed version.'
    elif kind=='AFFECTS_VERSION' and intervals(value) is None:reason='Version expression is unsupported; no guessed range.'
    elif supports and contradicts:status='CONFLICT';reason='Current scoped evidence explicitly contradicts the claim.'
    elif any(x.get('details',{}).get('classification')=='REJECTED' for x in current):
        status='REJECTED';reason='Static information explicitly rejects this association.'
    elif kind=='KNOWN_EXPLOITED' and value.get('known_exploited') is not True:reason='Catalog absence is not evidence of no exploitation.'
    elif kind=='AFFECTS_VERSION' and intervals(value) is None:reason='Version expression is unsupported; no guessed range.'
    elif kind=='FIXED_VERSION' and not value.get('version'):reason='No explicit normalized fixed version.'
    elif kind in ('POC_EXISTS','POC_ASSOCIATION'):
        groups=sorted(set(groups)|{x.get('lineage') or 'unresolved-origin' for x in supports if x.get('explicit') and
            x.get('evidence_type')=='repository_readme' and x.get('details',{}).get('classification')=='CONFIRMED'})
        if any(x.get('details',{}).get('classification')=='CONFIRMED' for x in supports) and len(groups)>=2:
            status='CONFIRMED';reason='Static association with an independent explicit reference; usability remains untested.'
        elif supports:status='PENDING';reason='Repository remains a static candidate; independent reference missing.'
    elif explicit_official or len(groups)>=2:status='CONFIRMED';reason='Explicit authoritative primary evidence or independent high-quality corroboration.'
    return {'status':status,'reason_summary':reason,'supporting_evidence':[x['id'] for x in supports],
        'contradicting_evidence':[x['id'] for x in contradicts],'considered':[x['id'] for x in current],
        'independent_groups':groups,'method':'deterministic-evidence-v1','abstention_reason':reason if status=='INSUFFICIENT_EVIDENCE' else None}

def compare_claims(a,b):
    if a['scope']!=b['scope']:return None
    ta,tb=a['type'],b['type'];va,vb=a['value'],b['value']
    if {ta,tb}=={'AFFECTS_VERSION','FIXED_VERSION'}:
        affected,fixed=(va,vb) if ta=='AFFECTS_VERSION' else (vb,va)
        return 'VERSION_CONFLICT' if contains(affected,fixed.get('version')) is True else None
    if ta!=tb:return None
    if ta=='FIXED_VERSION' and (not va.get('version') or not vb.get('version')):return None
    if ta=='AFFECTS_VERSION':
        ra,rb=intervals(va),intervals(vb)
        return 'VERSION_CONFLICT' if ra is not None and rb is not None and ra!=rb else None
    if canonical_value(ta,va)==canonical_value(tb,vb):return None
    return {'FIXED_VERSION':'FIXED_VERSION_CONFLICT','CVSS_SCORE':'SEVERITY_CONFLICT',
        'POC_EXISTS':'POC_STATUS_CONFLICT','POC_ASSOCIATION':'POC_STATUS_CONFLICT','PATCH_EXISTS':'PATCH_STATUS_CONFLICT',
        'FIX_COMMIT':'PATCH_STATUS_CONFLICT','KNOWN_EXPLOITED':'KNOWN_EXPLOITATION_CONFLICT','VENDOR_CONFIRMED':'VENDOR_THIRD_PARTY_CONFLICT'}.get(ta)
