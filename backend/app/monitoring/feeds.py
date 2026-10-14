"""Bounded UTF-8 RSS/Atom metadata only; no entity resolution or content execution."""
import re
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from datetime import timezone
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from app.monitoring.catalog import FEEDS
from app.utils.time import parse_time

def text(value):
    class Plain(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=True);self.parts=[]
        def handle_data(self,data):self.parts.append(data)
    p=Plain();p.feed(value or '');return ' '.join(''.join(p.parts).split())

def time(value):
    if not value:return None
    try:return parse_time(value)
    except ValueError:
        d=parsedate_to_datetime(value)
        if d.tzinfo is None:raise ValueError('Feed date needs timezone')
        return d.astimezone(timezone.utc)

def parse_feed(payload,key):
    if key not in FEEDS or not isinstance(payload,bytes) or len(payload)>2_000_000:raise ValueError('Unregistered or oversized feed')
    try:decoded=payload.decode('utf-8-sig')
    except UnicodeError:raise ValueError('Only UTF-8 feeds supported') from None
    if '<!DOCTYPE' in decoded or '<!ENTITY' in decoded or '\x00' in decoded:raise ValueError('DTD/entities and non-UTF8 encodings prohibited')
    try:root=ET.fromstring(decoded)
    except ET.ParseError:raise ValueError('Invalid RSS/Atom') from None
    if sum(1 for _ in root.iter())>10000:raise ValueError('Feed node limit exceeded')
    atom=root.tag=='{http://www.w3.org/2005/Atom}feed';prefix='{http://www.w3.org/2005/Atom}' if atom else ''
    if not atom and root.tag!='rss':raise ValueError('Unsupported feed format')
    entries=root.findall(prefix+'entry') if atom else root.findall('./channel/item');result=[]
    for i,item in enumerate(entries[:100]):
        get=lambda name:item.findtext(prefix+name)
        url=get('link')
        if atom:
            url=next((x.get('href') for x in item.findall(prefix+'link') if x.get('rel','alternate')=='alternate'),None)
            if not url:url=get('id')
        p=urlsplit(url or '')
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:continue
        if key=='ARXIV' and p.hostname in ('arxiv.org','export.arxiv.org'):url='https://arxiv.org'+p.path
        title=text(get('title'));content=text(get('summary') or get('description') or get('content') or '')
        identifier=get('id') if atom else get('guid')
        if not title or len(title)>2000 or len(content)>1_000_000:continue
        result.append({'external_id':identifier or url,'title':title,'content':content,'url':url,'document_type':FEEDS[key]['type'],
            'authors':[x.findtext(prefix+'name') for x in item.findall(prefix+'author') if x.findtext(prefix+'name')] if atom else [get('author')] if get('author') else [],
            'published_at':time(get('published') or get('pubDate')),'modified_at':time(get('updated')),
            'locator':{'xml_path':f'/feed/entry[{i+1}]' if atom else f'/rss/channel/item[{i+1}]'}})
    return result
