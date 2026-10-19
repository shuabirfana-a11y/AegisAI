"""Source-entry comparability, separate from provenance and trust decisions.

Parallel ranges are compatible only when bound source records explicitly describe
the same package-wide union. Version numbers alone never establish a branch.
"""
from copy import deepcopy
from typing import Any,Literal
import json
from hashlib import sha256
from packaging.version import Version,InvalidVersion
from packaging.utils import canonicalize_version
from pydantic import Field
from app.runtime.contracts import FrozenModel
from app.agents.contracts import fingerprint
from app.enrichment.versions import intervals,merge_intervals,canonical_value,contains

VERSION='version-comparability-v1'
Result=Literal['SAME_SCOPE','DIFFERENT_SCOPE','BRANCH_DIFFERENCE','BOUNDARY_DIFFERENCE',
               'NOT_COMPARABLE','INSUFFICIENT_CONTEXT','UNKNOWN','REAL_CONFLICT']

def _ranges(value):
    found=intervals(value)
    return tuple((canonicalize_version(lo) if lo is not None else None,li,canonicalize_version(hi) if hi is not None else None,ui)
                 for lo,li,hi,ui in found) if found is not None else None

def _release(value):
    try:
        parts=Version(value).release
        return {'major':parts[0],'minor':parts[1] if len(parts)>1 else None,'patch':parts[2] if len(parts)>2 else None}
    except (InvalidVersion,TypeError):return {'major':None,'minor':None,'patch':None}

class VersionScope(FrozenModel):
    normalization_version:Literal['version-comparability-v1']=VERSION
    ecosystem:Literal['PyPI']='PyPI'
    product:str|None=None
    component:str
    kind:Literal['AFFECTS_VERSION','FIXED_VERSION']
    value_hash:str
    record_union:tuple[tuple[str|None,bool,str|None,bool],...]=Field(max_length=128)
    predicate:tuple[tuple[str|None,bool,str|None,bool],...]=Field(max_length=128)
    coverage:Literal['SOURCE_ENTRY','RECORD_UNION']
    entry_keys:tuple[str,...]=Field(max_length=128)
    entries:tuple[dict[str,Any],...]=Field(max_length=128)
    branch:dict[str,Any]
    fixed_version:str|None=None
    raw_expression:str|None=None
    evidence_id:str
    raw_document_id:str
    raw_hash:str|None=None
    source_entry_pointer:str

class ScopeComparison(FrozenModel):
    result:Result
    reason:str
    evidence_ids:tuple[str,...]=()

class VersionScopeNormalizer:
    def normalize(self,kind,value,*,document,locator,evidence_id,raw_document_id,raw_hash=None,integrity_verified=False):
        if not integrity_verified or kind not in ('AFFECTS_VERSION','FIXED_VERSION') or value.get('ecosystem')!='PyPI':return None
        if any(value.get(k) for k in ('condition','platform','architecture')):return None
        package=value.get('package')
        if not isinstance(package,str) or not package:return None
        record=document.get('record',document) if isinstance(document,dict) else None
        if not isinstance(record,dict):return None
        prefix='/record' if 'record' in document else ''
        clauses=[]
        for index,item in enumerate(record.get('affected',record.get('vulnerabilities',[]))):
            if not isinstance(item,dict):return None
            identity=item.get('package') or {};eco=identity.get('ecosystem')
            if eco=='pip':eco='PyPI'
            if eco!='PyPI' or identity.get('name')!=package:continue
            if any(item.get(k) for k in ('condition','platform','architecture','ecosystem_specific')):return None
            if 'affected' in record:
                entry=f'{prefix}/affected/{index}'
                for j,part in enumerate(item.get('ranges',[])):
                    val={'ecosystem':'PyPI','events':part.get('events'),'range_type':part.get('type'),
                         'explicit_versions':item.get('versions')}
                    parsed=_ranges(val)
                    if parsed is None:return None
                    fixes=[v['fixed'] for v in part.get('events',[]) if 'fixed' in v]
                    # An episodic event log needs an event-to-fix association;
                    # this bounded adapter must not flatten several fixes.
                    if len(fixes)>1:return None
                    clauses.append({'pointer':entry+f'/ranges/{j}','ranges':parsed,'fixed':tuple(fixes)})
            else:
                entry=f'{prefix}/vulnerabilities/{index}'
                parsed=_ranges({'ecosystem':'PyPI','range':item.get('vulnerable_version_range')})
                if parsed is None:return None
                fixed=item.get('first_patched_version') or item.get('patched_versions')
                # A patched constraint is handled by the existing bound-field adapter.
                try:fixed=str(Version(fixed)) if fixed else None
                except (InvalidVersion,TypeError):fixed=None
                clauses.append({'pointer':entry,'ranges':parsed,'fixed':(fixed,) if fixed else ()})
        if not clauses or len(clauses)>128:return None
        union=merge_intervals([(Version(lo) if lo is not None else None,li,Version(hi) if hi is not None else None,ui)
                               for c in clauses for lo,li,hi,ui in c['ranges']])
        complete=tuple((canonicalize_version(lo) if lo is not None else None,li,canonicalize_version(hi) if hi is not None else None,ui) for lo,li,hi,ui in union)
        point=value.get('version') if kind=='FIXED_VERSION' else None
        parsed=_ranges(value) if kind=='AFFECTS_VERSION' else None
        if kind=='FIXED_VERSION':
            try:point=str(Version(point))
            except (InvalidVersion,TypeError):return None
            matched=[c for c in clauses if point in c['fixed']]
        else:matched=[c for c in clauses if parsed==c['ranges']]
        coverage='SOURCE_ENTRY'
        if kind=='AFFECTS_VERSION' and parsed==complete:matched=clauses;coverage='RECORD_UNION'
        pointer=(locator or {}).get('json_pointer')
        # range_id-only references and unbound/foreign pointers cannot waive conflicts.
        if not isinstance(pointer,str) or not any(pointer==c['pointer'] or pointer.startswith(c['pointer']+'/') for c in matched):return None
        if not matched:return None
        selected=merge_intervals([(Version(lo) if lo is not None else None,li,Version(hi) if hi is not None else None,ui)
                                  for c in matched for lo,li,hi,ui in c['ranges']])
        predicate=parsed if kind=='AFFECTS_VERSION' else tuple((canonicalize_version(lo) if lo is not None else None,li,canonicalize_version(hi) if hi is not None else None,ui) for lo,li,hi,ui in selected)
        entries=tuple({'source_entry':c['pointer'],'ranges':c['ranges'],'fixed_versions':c['fixed'],
                       'release_parts':[_release(v) for v in c['fixed']]} for c in matched)
        return VersionScope(product=value.get('product') if isinstance(value.get('product'),str) else None,
            component=package,kind=kind,value_hash=fingerprint(canonical_value(kind,value)),record_union=complete,
            predicate=predicate,coverage=coverage,entry_keys=tuple(sorted({fingerprint([c['ranges'],c['fixed']]) for c in matched})),
            entries=entries,branch={'declared':value.get('branch'),'source_entries':[c['pointer'] for c in matched]},
            fixed_version=point,raw_expression=value.get('range') or value.get('raw_expression') or point,
            evidence_id=str(evidence_id),raw_document_id=str(raw_document_id),raw_hash=raw_hash,source_entry_pointer=pointer)

def source_scopes(assertion):
    found=[];normalizer=VersionScopeNormalizer();kind=assertion['type'];value=assertion['value']
    for data in assertion.get('version_scopes',[]):
        try:scope=VersionScope.model_validate(data)
        except (ValueError,TypeError):continue
        if scope.kind==kind and scope.value_hash==fingerprint(canonical_value(kind,value)):
            found.append(scope)
    for context in assertion.get('version_source_contexts',[]):
        try:scope=normalizer.normalize(kind,value,**context)
        except (ValueError,TypeError,KeyError):scope=None
        if scope:found.append(scope)
    return tuple(found)

def compare_scopes(a,b):
    va,vb=a['value'],b['value']
    for key in ('ecosystem','package','product','condition','platform','architecture'):
        if va.get(key) and vb.get(key) and va[key]!=vb[key]:
            return ScopeComparison(result='NOT_COMPARABLE',reason='Different explicit '+key)
    left,right=source_scopes(a),source_scopes(b)
    if not left or not right:return ScopeComparison(result='INSUFFICIENT_CONTEXT',reason='Source-entry association not proven')
    verdicts=[]
    for x in left:
        for y in right:
            ids=(x.evidence_id,y.evidence_id)
            if x.component!=y.component or x.product and y.product and x.product!=y.product:
                verdicts.append(ScopeComparison(result='NOT_COMPARABLE',reason='Different package/product identity',evidence_ids=ids));continue
            if x.record_union!=y.record_union:
                verdicts.append(ScopeComparison(result='BOUNDARY_DIFFERENCE',reason='Complete source unions differ; original conflict retained',evidence_ids=ids));continue
            if x.predicate==y.predicate:
                if {x.kind,y.kind}=={'AFFECTS_VERSION','FIXED_VERSION'} and contains(
                    va if x.kind=='AFFECTS_VERSION' else vb,y.fixed_version if y.kind=='FIXED_VERSION' else x.fixed_version) is True:
                    verdicts.append(ScopeComparison(result='REAL_CONFLICT',reason='Same-entry fixed release is explicitly still affected',evidence_ids=ids))
                elif x.kind==y.kind=='FIXED_VERSION' and x.fixed_version!=y.fixed_version:
                    verdicts.append(ScopeComparison(result='REAL_CONFLICT',reason='Different explicit fixes for the same source range',evidence_ids=ids))
                else:verdicts.append(ScopeComparison(result='SAME_SCOPE',reason='Same bound range scope',evidence_ids=ids))
            elif x.coverage=='RECORD_UNION' or y.coverage=='RECORD_UNION':
                verdicts.append(ScopeComparison(result='DIFFERENT_SCOPE',reason='Local entry and compatible full-record union',evidence_ids=ids))
            elif set(x.entry_keys).isdisjoint(y.entry_keys):
                verdicts.append(ScopeComparison(result='BRANCH_DIFFERENCE',reason='Distinct source-bound maintenance entries in the same complete record union',evidence_ids=ids))
            else:verdicts.append(ScopeComparison(result='UNKNOWN',reason='Overlapping entry associations unresolved',evidence_ids=ids))
    # A conflicting/unresolved pair cannot be hidden by selecting a favorable proof.
    unsafe=[v for v in verdicts if v.result not in ('SAME_SCOPE','DIFFERENT_SCOPE','BRANCH_DIFFERENCE','NOT_COMPARABLE')]
    if unsafe:return unsafe[0]
    return next((v for v in verdicts if v.result in ('BRANCH_DIFFERENCE','DIFFERENT_SCOPE')),verdicts[0])

def stored_scope(session,evidence,kind):
    """Bind a derived scope to the existing immutable raw/excerpt witnesses."""
    from app.db import models as m
    from app.enrichment.evidence import pointer
    raw=session.get(m.RawDocument,evidence.raw_document_id) if evidence.raw_document_id else None
    if raw is None or raw.source_id!=evidence.source_id or sha256(raw.raw_payload).hexdigest()!=raw.content_hash:return None
    observation=session.get(m.SourceObservation,evidence.observation_id) if evidence.observation_id else None
    if (observation is None or observation.source_id!=evidence.source_id or observation.raw_document_id!=raw.id
        or observation.parse_status!='parsed'):return None
    if sha256(evidence.excerpt.encode('utf-8')).hexdigest()!=evidence.excerpt_hash:return None
    try:
        document=json.loads(raw.raw_payload)
        fragment=pointer(document,evidence.locator['json_pointer'])
        if evidence.excerpt!=json.dumps(fragment,ensure_ascii=False)[:2400]:return None
        return VersionScopeNormalizer().normalize(kind,evidence.observed_value or {},document=document,
            locator=evidence.locator,evidence_id=str(evidence.id),raw_document_id=str(raw.id),raw_hash=raw.content_hash,
            integrity_verified=True)
    except (ValueError,TypeError,KeyError,IndexError):return None

def evidence_scopes(evidence,kind):
    data=evidence.details.get('normalized_version_scope')
    if not data:return ()
    try:scope=VersionScope.model_validate(data)
    except (ValueError,TypeError):return ()
    if (scope.kind!=kind or scope.evidence_id!=evidence.evidence_id or scope.raw_document_id!=str(evidence.raw_document_id)
        or scope.raw_hash!=evidence.hash or scope.value_hash!=fingerprint(canonical_value(kind,evidence.observed_value))):return ()
    return (scope.model_dump(mode='json'),)
