"""PyPI interval semantics; never infer a fixed release from an affected upper bound."""
from packaging.version import Version,InvalidVersion
from app.services.versions import parse_expression,parse_events

def intervals(value):
    if value.get('ecosystem','PyPI')!='PyPI' or value.get('parse_status') in ('unsupported','failed'):return None
    if 'ranges' in value:
        result=[]
        for part in value['ranges']:
            parsed=intervals({**part,'ecosystem':value.get('ecosystem','PyPI')})
            if parsed is None:return None
            result.extend(parsed)
        return merge_intervals(result) if result else None
    if value.get('events') is not None or value.get('explicit_versions'):
        parsed=parse_events(value.get('events'),range_type=value.get('range_type','ECOSYSTEM'),versions=value.get('explicit_versions'))
    else:
        parsed=parse_expression(value.get('range',value.get('raw_expression','')))
        # A comma-separated expression is a conjunction of bounds, not a chronological event log.
        if parsed['parse_status']=='parsed' and not parsed.get('explicit_versions'):
            events=[{'introduced':parsed.get('introduced') or '0'}]
            if parsed.get('fixed'):events.append({'fixed':parsed['fixed']})
            elif parsed.get('last_affected'):events.append({'last_affected':parsed['last_affected']})
            parsed={**parsed,'events':events}
    if parsed['parse_status']!='parsed':return None
    result=[];start=None;opened=False
    try:
        for event in parsed.get('events') or []:
            key,version=next(iter(event.items()))
            if key=='introduced':start=None if version=='0' else Version(version);opened=True
            else:
                if not opened:start=None
                result.append((start,True,Version(version),key=='last_affected'));opened=False;start=None
        if opened or not result and not parsed.get('explicit_versions'):result.append((start,True,None,False))
        for version in parsed.get('explicit_versions') or []:result.append((Version(version),True,Version(version),True))
    except (InvalidVersion,TypeError,ValueError):return None
    return merge_intervals(result)

def merge_intervals(result):
    merged=[]
    for item in sorted(result,key=lambda x:(x[0] is not None,x[0] or Version('0'))):
        if not merged:merged.append(item);continue
        lo,li,hi,ui=merged[-1];nlo,nli,nhi,nui=item
        if hi is None or nlo is None or nlo<hi or nlo==hi and (ui or nli):
            if hi is None:continue
            if nhi is None or nhi>hi:merged[-1]=(lo,li,nhi,nui)
            elif nhi==hi:merged[-1]=(lo,li,hi,ui or nui)
        else:merged.append(item)
    return merged

def contains(value,version):
    ranges=intervals(value)
    try:v=Version(version)
    except (InvalidVersion,TypeError):return None
    if ranges is None:return None
    return any((lo is None or v>lo or li and v==lo) and (hi is None or v<hi or ui and v==hi) for lo,li,hi,ui in ranges)

def version_key(version):
    v=Version(version);release=list(v.release)
    while len(release)>1 and release[-1]==0:release.pop()
    return [v.epoch,release,v.pre,v.post,v.dev,v.local]

def canonical_value(kind,value):
    result={k:v for k,v in value.items() if k not in ('raw_expression','locator','parse_reason')}
    if kind=='AFFECTS_VERSION':
        ranges=intervals(value)
        if ranges is not None:
            return {'ecosystem':value.get('ecosystem','PyPI'),'package':value.get('package'),
                'intervals':[[version_key(str(lo)) if lo is not None else None,li,version_key(str(hi)) if hi is not None else None,ui] for lo,li,hi,ui in ranges]}
    if kind=='FIXED_VERSION' and value.get('version'):
        try:return {'ecosystem':value.get('ecosystem','PyPI'),'package':value.get('package'),'version':version_key(value['version'])}
        except InvalidVersion:pass
    return result
