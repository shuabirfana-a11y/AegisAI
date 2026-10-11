from datetime import datetime,timezone

def utcnow(): return datetime.now(timezone.utc)

def parse_time(value):
    if value is None or value=='': return None
    if not isinstance(value,str): raise ValueError('Source timestamp must be a string')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:
        if len(value)==10: result=result.replace(tzinfo=timezone.utc)
        else: raise ValueError('Source timestamp lacks timezone')
    return result.astimezone(timezone.utc)
