import json,re
from packaging.version import Version,InvalidVersion

PARSER_VERSION='version-v0.1'

def blank(raw_expression,**extra):
    return {'raw_expression':raw_expression,'parse_status':'unsupported','parse_reason':'Unsupported expression/ecosystem',
            'introduced':None,'fixed':None,'last_affected':None,'limit_version':None,'events':None,'explicit_versions':None,
            'parser_version':PARSER_VERSION,**extra}

def parse_expression(raw_expression, ecosystem='PyPI'):
    result=blank(raw_expression,range_type='ECOSYSTEM')
    if not isinstance(raw_expression,str) or not raw_expression.strip():
        return {**result,'parse_status':'failed','parse_reason':'Empty expression'}
    if ecosystem!='PyPI': return result
    tokens=raw_expression.split(','); values={}; events=[]
    try:
        for token in tokens:
            match=re.fullmatch(r'\s*(>=|<=|<|==)\s*([^\s,]+)\s*',token)
            if not match: return result
            operator,value=match.groups(); Version(value)
            key={'>=':'introduced','<':'fixed','<=':'last_affected','==':'explicit_versions'}[operator]
            if key in values: return result
            values[key]=[value] if key=='explicit_versions' else value
            if key!='explicit_versions': events.append({key:value})
        if 'fixed' in values and 'last_affected' in values: return result
        if 'explicit_versions' in values and len(values)>1: return result
        lower=values.get('introduced'); upper=values.get('fixed',values.get('last_affected'))
        if lower and upper and (Version(lower)>Version(upper) or ('fixed' in values and Version(lower)==Version(upper))): return result
    except InvalidVersion: return result
    return {**result,**values,'events':events or None,'parse_status':'parsed','parse_reason':None}

def parse_events(events, ecosystem='PyPI', range_type='ECOSYSTEM', versions=None):
    result=blank(json.dumps({'type':range_type,'events':events,'versions':versions},ensure_ascii=False,separators=(',',':')),
                 range_type=range_type,events=events,explicit_versions=versions)
    if ecosystem!='PyPI' or range_type!='ECOSYSTEM': return result
    if not events and not versions: return result
    first={}; open_start=None
    try:
        for event in events or []:
            if len(event)!=1: return result
            key,value=next(iter(event.items()))
            if key not in ('introduced','fixed','last_affected','limit') or not isinstance(value,str): return result
            if value!='0' or key!='introduced': Version(value)
            if key=='introduced':
                if open_start is not None: return result
                open_start=value
            else:
                if open_start is None: return result
                if open_start!='0' and (Version(open_start)>Version(value) or (key in ('fixed','limit') and Version(open_start)==Version(value))): return result
                open_start=None
            storage_key='limit_version' if key=='limit' else key
            first.setdefault(storage_key,value)
        for value in versions or []: Version(value)
    except (InvalidVersion,TypeError): return result
    return {**result,**first,'parse_status':'parsed','parse_reason':None}
