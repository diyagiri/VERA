"""Capture fixed official URLs, parse headings, and retain auditable source versions.
Raw bytes stay in ignored data/snapshots/v2. No policy approval or unrestricted crawl.
"""
import argparse, hashlib, html, json, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/'data/evidence/registry.json'
ALLOWED={'www.canada.ca','ircc.canada.ca','www.welcomebc.ca','studentaidbc.ca','www.sfu.ca','students.ubc.ca'}
MAX_BYTES=15_000_000

def valid_url(url):
    p=urllib.parse.urlsplit(url)
    return p.scheme=='https' and p.hostname in ALLOWED and not p.username and not p.password and p.port in (None,443)

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections=3
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not valid_url(newurl): raise ValueError('Redirect outside official allowlist')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def clean(text): return re.sub(r'\s+',' ',html.unescape(text)).strip()

class Sections(HTMLParser):
    """Dependency-free extraction excluding navigation, scripts and form contents."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip=0; self.active=None; self.parts=[]; self.blocks=[]
        self.section='Introduction'; self.anchor=''; self.headings=[]; self.modified=None; self.title=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style','nav','footer','header','form'): self.skip+=1
        if self.skip:return
        if tag=='meta' and a.get('name',a.get('property','')).lower() in ('dcterms.modified','dc.date.modified','date','last-modified','article:modified_time'):
            self.modified=a.get('content')
        if tag in ('h1','h2','h3','h4','p','li','dt','dd'):
            if self.active:self.finish_block()
            self.active=tag; self.parts=[]; self.block_anchor=a.get('id','')
    def handle_data(self,data):
        if not self.skip and self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag in ('script','style','nav','footer','header','form') and self.skip:
            self.skip-=1;return
        if self.skip or tag!=self.active:return
        self.finish_block()
    def finish_block(self):
        tag=self.active
        text=clean(' '.join(self.parts))
        if text:
            if tag.startswith('h'):
                self.section=text;self.anchor=self.block_anchor
                self.headings.append({'text':text,'anchor':self.anchor})
                if tag=='h1':self.title=text
            else:self.blocks.append({'section':self.section,'anchor':self.anchor,'text':text})
        self.active=None;self.parts=[]

def parse_html(raw):
    decoded=raw.decode('utf-8',errors='replace')
    main=re.search(r'<main\b[^>]*>(.*?)</main>',decoded,re.I|re.S)
    body=main.group(1) if main else decoded
    h1=re.search(r'<h1\b',body,re.I)
    if h1:body=body[h1.start():]
    parsed=Sections();parsed.feed(body)
    meta=Sections();meta.feed(decoded[:decoded.lower().find('</head>')+7])
    parsed.modified=meta.modified or parsed.modified
    return parsed

PREFERRED={
'D02':r'eligible|admissib|service','D03':r'eligib|admissib|permanent|r[eé]sident',
'D09':r'before opening|avant d|identification|identit','D10':r'compar|contact|communiquer',
'D11':r'immigration status|statut d.immigrant|residency status|statut de r[eé]sidence',
'D12':r'after applying|apr[eè]s|overview|aper[cç]u','D13':r'how to apply|comment faire|gather|rassembler',
'D14':r'family benefit|prestation familiale','D15':r'benefit|prestation','D17':r'money|financ',
'D18':r'money management|financ|notions','D20':r'eligibility criteria|crit[eè]res',
'D21':r'^introduction$|^determining|^d[eé]termination|residential ties|liens de r[eé]sidence'}

def short_excerpt(source,parsed):
    """At most one complete sentence of <=25 words, never an interactive outcome."""
    if source['id']=='D03':return None  # Time-limit conditions cannot be represented by one isolated sentence.
    preferred=re.compile(PREFERRED.get(source['id'],'.'),re.I)
    for b in parsed.blocks:
        if not preferred.search(b['section']):continue
        if any(x in b['section'].lower() for x in ('you may be eligible','meet all','vous pourriez','vous répondez')):continue
        for sentence in re.split(r'(?<=[.!?])\s+',b['text']):
            count=len(sentence.split())
            if 9<=count<=25 and sentence[-1:] in '.!?' and not re.match(r'^(Il |Elle |This |These |Ces |Choisir)',sentence):
                return {'text':sentence,'section':b['section'],'anchor':b['anchor'],'word_count':count,'complete_sentence':True}
    return None

def capture(source,locale='en',attempts=2):
    url=source['url'] if locale=='en' else source['fr_url'];doc_id=source['id']+'-'+locale
    if not valid_url(url):raise ValueError('Source is not allowlisted')
    req=urllib.request.Request(url,headers={'User-Agent':'VERA-public-source-review/2.1 (bounded educational prototype)'})
    for attempt in range(attempts):
        try:
            with urllib.request.build_opener(SafeRedirect()).open(req,timeout=20) as response:
                raw=response.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise ValueError('Document exceeds capture limit')
                resolved=response.url;content_type=response.headers.get('Content-Type','')
                header_modified=response.headers.get('Last-Modified')
                break
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
            if attempt+1==attempts or getattr(exc,'code',0) in (401,403,404,429):raise
            time.sleep(.5*(attempt+1))
    sha=hashlib.sha256(raw).hexdigest();folder=ROOT/'data/snapshots/v2';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(doc_id+'-'+sha[:16]+'.capture')
    if not path.exists():path.write_bytes(raw)
    now=datetime.now(timezone.utc)
    result={'id':doc_id,'document_id':doc_id,'source_id':source['id'],'locale':locale,'original_url':url,
      'resolved_url':resolved,'retrieved_at':now.isoformat(),
      'checked_on':now.astimezone(ZoneInfo('America/Vancouver')).date().isoformat(),
      'snapshot_sha256':sha,'content_type':content_type,'publisher_http_last_modified':header_modified,
      'path':str(path.relative_to(ROOT)),'byte_length':len(raw),'human_reviewed_on':None,
      'policy_effective_from':None,'policy_effective_to':None,'review_status':'automated_capture_not_policy_approval',
      'reuse_status':source['reuse_policy'],'reuse_terms_url':source['reuse_terms_url'],
      'policy_approval_changed':False,'source_text_excerpt':None}
    return extract_result(result,raw,source)

def extract_result(result,raw,source):
    content_type=result.get('content_type','')
    result=dict(result)
    result['source_text_excerpt']=None
    result.pop('excerpt_gap',None)
    result['extractor_version']='html-sections-2.1'
    if 'pdf' in content_type or raw[:4]==b'%PDF':
        result.update(status='captured_pdf_link_only',extraction_status='not_extracted_pending_page_visual_review',
          heading_locators=[],publisher_modified_on=None,
          coverage_limit='PDF bytes captured and hashed only; no PDF text used in runtime guidance.')
    else:
        parsed=parse_html(raw)
        result.update(status='captured',extraction_status='html_sections_parsed',heading_locators=parsed.headings,
          publisher_modified_on=parsed.modified,extracted_paragraphs=len(parsed.blocks),captured_title=parsed.title,
          extracted_text_sha256=hashlib.sha256('\n'.join(b['text'] for b in parsed.blocks).encode()).hexdigest())
        if not parsed.blocks:result.update(status='captured_parse_gap',extraction_status='no_usable_paragraphs')
        elif source['reuse_policy']=='canada_noncommercial_attributed_short_extract':
            excerpt=short_excerpt(source,parsed)
            if excerpt:result['source_text_excerpt']=excerpt
            else:result['excerpt_gap']=('Time-limit conditions require the complete context; no isolated sentence published.' if source['id']=='D03' else 'No complete short sentence found in selected sections; original paraphrase only.')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ids',nargs='+')
    p.add_argument('--locales',nargs='+',choices=['en','fr'],default=['en','fr'])
    p.add_argument('--reextract-report',help='Reparse previously captured bytes without network access')
    p.add_argument('--output',required=True);args=p.parse_args();output=Path(args.output)
    if output.exists():p.error('Use a new report path; capture history is immutable')
    registry=json.loads(REGISTRY.read_text());sources={s['id']:s for s in registry['sources']};ids=args.ids or list(sources)
    if set(ids)-sources.keys():p.error('Only known registry source IDs are accepted')
    cached={}
    if args.reextract_report:
        old=json.loads(Path(args.reextract_report).read_text())
        cached={c['document_id']:c for c in old['captures']}
    captures=[]
    for sid in ids:
        s=sources[sid]
        for locale in args.locales:
            if locale=='fr' and not s.get('fr_url'):continue
            try:
                if args.reextract_report:
                    prior=cached[sid+'-'+locale]
                    if not prior['status'].startswith('captured'):raise ValueError('Prior capture was unavailable')
                    local=(ROOT/prior['path']).resolve()
                    if not local.is_relative_to((ROOT/'data/snapshots/v2').resolve()):raise ValueError('Invalid snapshot path')
                    raw=local.read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=prior['snapshot_sha256']:raise ValueError('Snapshot hash mismatch')
                    item=extract_result(prior,raw,s)
                else:item=capture(s,locale)
            except Exception as exc:
                item={'id':sid+'-'+locale,'document_id':sid+'-'+locale,'source_id':sid,'locale':locale,
                  'status':'failed','error_type':type(exc).__name__,'http_status':getattr(exc,'code',None),'human_reviewed_on':None}
            captures.append(item);print(json.dumps({'document':item['id'],'status':item['status']}),flush=True);time.sleep(.15)
    report={'schema_version':2,'registry_sha256':hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
      'generated_at':datetime.now(timezone.utc).isoformat(),'reextracted_from':args.reextract_report,'captures':captures,'policy_approvals_changed':False,'human_reviews_performed':0}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    counts={'captured':sum(x['status'].startswith('captured') for x in captures),'failed':sum(x['status']=='failed' for x in captures),'report':str(output)}
    print(json.dumps(counts));return int(counts['failed']>0)
if __name__=='__main__':sys.exit(main())
