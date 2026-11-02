#!/usr/bin/env python3
"""Polite, conservative OP-18 monitor for a GitHub Pages PWA.

This does not make purchases or bypass access controls. A ticket is marked
available only after a publicly readable Shopify ticket product JSON confirms
availability for its matching event/date. Store calendar discoveries are
flagged for review, not treated as purchasable inventory.
"""
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlparse, urlunparse
import requests

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/status.json'
SEED=ROOT/'data/seed.json'
TZ=dt.timezone(dt.timedelta(hours=-5))  # Events are in EST after Nov 1
UA='OP18Radar/1.0 (+public store page watcher; contact store for registration)'
HEADERS={'User-Agent':UA, 'Accept':'application/json,text/html;q=0.9,*/*;q=0.8'}
DATE_PATTERN=re.compile(r'(op[- ]?18|the dominance of god)',re.I)
EVENT_PATTERN=re.compile(r'(pre[- ]?release|release event|event ticket|prerelease|ticket)',re.I)
EXCLUDE_PATTERN=re.compile(r'(booster box|booster pack|sealed box|display box|booster case|pre.?order)',re.I)

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.href='';self.text=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            self.href=dict(attrs).get('href','');self.text=[]
    def handle_data(self,data):
        if self.href:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href:
            self.links.append((self.href,' '.join(self.text).strip()));self.href='';self.text=[]

def get(url,expect_json=False):
    r=requests.get(url,headers=HEADERS,timeout=14,allow_redirects=True)
    r.raise_for_status()
    if expect_json:
        if 'html' in r.headers.get('content-type',''):
            raise ValueError('Product JSON endpoint returned HTML')
        return r.json()
    return r.text

def product_js(url):
    parts=urlparse(url)
    if '/products/' not in parts.path:return None
    # Shopify publicly exposed product details, when allowed by the shop.
    product_path=parts.path.split('/products/')[0]+'/products/'+parts.path.split('/products/')[1].split('/')[0]
    js_url=urlunparse((parts.scheme,parts.netloc,product_path+'.js','','',''))
    try:
        js=get(js_url,True)
        if isinstance(js,dict) and isinstance(js.get('variants'),list):
            name=str(js.get('title',''))
            if not DATE_PATTERN.search(name) or not EVENT_PATTERN.search(name):
                return None
            return js
    except (ValueError,requests.RequestException,json.JSONDecodeError):pass
    return None

def event_match(event,variant):
    name=' '.join(str(variant.get(k) or '') for k in ('title','option1','option2','option3')).lower()
    try: d=dt.date.fromisoformat(event['date'])
    except ValueError:return False
    variants=[f'{d:%B} {d.day}',f'{d:%b} {d.day}',f'{d.day} {d:%B}',f'{d.day} {d:%b}',str(d)]
    # Matches "November 21" / "Nov 21" and optional suffix "21st"
    name=re.sub(r'(\d+)(st|nd|rd|th)\b',r'\1',name)
    return any(x.lower() in name for x in variants)

def variant_result(e,product):
    variants=product['variants']
    if not variants:return None,'Product has no variants'
    matched=[v for v in variants if event_match(e,v)]
    if matched:
        return ('available' if any(v.get('available') is True for v in matched) else 'sold_out'),f'Confirmed {len(matched)} date-matched Shopify variant(s)'
    if len(variants)==1:
        return ('available' if variants[0].get('available') is True else 'sold_out'),'Single Shopify ticket variant confirmed'
    if all(v.get('available') is False for v in variants):
        return 'sold_out','All Shopify ticket variants sold out'
    return None,'Date-specific variant could not be confidently matched — manual review required'

def discover(html,base_url):
    parser=Links();parser.feed(html)
    seen={};domain=urlparse(base_url).netloc.replace('www.','')
    for href,label in parser.links:
        url=urljoin(base_url,href)
        parts=urlparse(url)
        if parts.scheme not in {'https','http'} or parts.netloc.replace('www.','')!=domain:continue
        text=' '.join((label,parts.path.replace('-',' ')))
        if not DATE_PATTERN.search(text) or not EVENT_PATTERN.search(text) or EXCLUDE_PATTERN.search(text):continue
        cleaned=urlunparse((parts.scheme,parts.netloc,parts.path,'','',''))
        seen[cleaned]=label.strip()[:160] or 'Potential OP-18 event listing'
    return [{'url':k,'title':v} for k,v in seen.items()]

def append(activity,type_,message,now):
    activity.insert(0,dict(id=hashlib.sha1((type_+message+now).encode()).hexdigest()[:14],type=type_,message=message,timestamp=now))

def main():
    saved=json.loads(DATA.read_text()) if DATA.exists() else json.loads(SEED.read_text())
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    today=dt.datetime.now(TZ).date().isoformat()
    activity=saved.setdefault('activity',[])
    checks=[]
    event_by_store={s['id']:[e for e in saved['events'] if e['storeId']==s['id']] for s in saved['stores']}
    known_urls={e.get('url','').rstrip('/') for e in saved['events']}
    discovered_urls={d['url'] for d in saved.setdefault('discoveries',[])}
    ok_pages=0
    for store in saved['stores']:
        store_id=store['id'];page=store.get('eventsUrl') or store.get('url')
        ok=False;message='No public event page URL configured'
        if page:
            try:
                body=get(page)
                ok=True;ok_pages+=1;message='Store page fetched; event links examined'
                for candidate in discover(body,page):
                    if candidate['url'].rstrip('/') in known_urls or candidate['url'] in discovered_urls:continue
                    uid=hashlib.sha1(candidate['url'].encode()).hexdigest()[:12]
                    saved['discoveries'].append({'id':uid,'storeId':store_id,'title':candidate['title'],'url':candidate['url'],'firstSeen':today,'status':'unverified'})
                    discovered_urls.add(candidate['url'])
                    append(activity,'discovery',f'Possible OP-18 listing at {store["name"]}: {candidate["title"]} — inspect official page before assuming tickets are live.',now)
            except (requests.RequestException,ValueError) as ex:
                message=f'Public page check unavailable ({type(ex).__name__}); not proof of sold out'
        # Verify only direct event ticket product pages, not generic calendar pages.
        cache={}
        for event in event_by_store.get(store_id,[]):
            url=event.get('url','')
            if '/products/' not in url:continue
            if url not in cache:
                cache[url]=product_js(url)
            product=cache[url]
            if product is None:continue
            new,reason=variant_result(event,product)
            if new is None:
                message='Ticket product found, but date-specific availability is uncertain'
                continue
            old=event.get('status')
            event['status']=new
            event['lastVerified']=today
            event['statusSource']='Shopify ticket product JSON'
            ok=True;message='Ticket inventory checked from public product JSON'
            if old!=new:
                action='available' if new=='available' else 'sold_out'
                append(activity,action,f'{store["name"]}: {event["date"]} {event["time"]} changed from {old} to {new}. Verify at {event["url"]}',now)
        checks.append({'storeId':store_id,'ok':ok,'message':message})
        time.sleep(0.45)  # A small courtesy pause between stores.
    saved['checks']=checks
    saved['activity']=activity[:80]
    saved['discoveries']=saved['discoveries'][-100:]
    saved['meta']['lastChecked']=now
    saved['meta']['checker']=f'Public store pages scanned ({ok_pages}/{len(saved["stores"])} fetched)'
    DATA.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
    print(f'{saved["meta"]["checker"]}; events={len(saved["events"])}; discoveries={len(saved["discoveries"])}')

if __name__=='__main__':main()
