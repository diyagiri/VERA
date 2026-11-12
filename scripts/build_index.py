"""Build portable versioned evidence JSON (and optional SQLite) from a saved capture.
No network calls, model downloads, embeddings, human-review claims or policy approval.
"""
import argparse,hashlib,json,re,sqlite3,sys,unicodedata
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def tokens(text):
    text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
    return sorted(set(re.findall(r'[^\W_]+',text,re.UNICODE)))

def build(output='data/evidence/index.json',capture_report=None,sqlite_output=None):
    registry=json.loads((ROOT/'data/evidence/registry.json').read_text())
    reports=sorted((ROOT/'data/evidence').glob('capture-*.json'),key=lambda p: json.loads(p.read_text()).get('generated_at',''))
    report_path=Path(capture_report) if capture_report else (reports[-1] if reports else None)
    if not report_path:raise ValueError('Run scripts/ingest_sources.py first')
    report=json.loads(report_path.read_text())
    sources={s['id']:s for s in registry['sources']}
    documents=[];chunks=[];gaps=[];seen=set()
    for c in report['captures']:
        sid=c['source_id'];locale=c['locale'];did=c['document_id']
        if did in seen or sid not in sources:raise ValueError('Unknown or duplicate capture ID')
        seen.add(did);s=sources[sid]
        doc={k:v for k,v in c.items() if k not in ('path','source_text_excerpt','heading_locators')}
        doc.update(title=s['title'],official_page_heading=c.get('captured_title'),publisher=s['publisher'],topic=s['topic'],
          jurisdiction=s['jurisdiction'],institution=s.get('institution'),campus=s.get('campus'),
          freshness_days=s['freshness_days'],content_version=c.get('snapshot_sha256'),
          locator_catalog=c.get('heading_locators',[]),human_reviewed=False,
          reuse_terms_url=s['reuse_terms_url'],applicability_limit=s.get('limits') or
          'Discovery and preparation only; program conditions and exceptions require official confirmation.')
        documents.append(doc)
        if c['status']!='captured':
            gaps.append({'document_id':did,'kind':c['status'],'detail':c.get('coverage_limit') or c.get('error_type') or c.get('extraction_status')})
            continue
        summary=s.get('summary',{}).get(locale)
        if not summary:
            gaps.append({'document_id':did,'kind':'missing_localized_summary'});continue
        e=c.get('source_text_excerpt')
        section=e['section'] if e else s.get('section') or 'Overview'
        url=c['resolved_url'];locator=url+('#'+e['anchor'] if e and e.get('anchor') else '')
        related=[other+'-'+locale for other in s.get('related_source_ids',[])]
        text=summary
        if e:text+='\n'+('Source excerpt: ' if locale=='en' else 'Extrait de la source : ')+e['text']
        cid=sid+'.'+locale+'.preparation'
        chunks.append({'id':cid,'source_id':sid,'document_id':did,'source_version':c['snapshot_sha256'],
          'locale':locale,'topic':s['topic'],'jurisdiction':s['jurisdiction'],
          'institution':s.get('institution'),'campus':s.get('campus'),
          'title':doc['title'],'publisher':s['publisher'],'section':section,'locator':locator,'url':url,
          'text':text,'text_kind':'original_paraphrase_with_short_official_excerpt' if e else 'original_paraphrase',
          'summary_text':summary,'localized_summary':s.get('summary',{}),'verbatim_excerpt':e['text'] if e else None,
          'excerpt_word_count':e['word_count'] if e else 0,'quote_is_complete_sentence':True if e else None,
          'context_limit':'Short preparation evidence, not complete program policy. Consult related sources and official page for conditions.',
          'related_document_ids':related,'related_chunk_ids':[x+'.'+locale+'.preparation' for x in s.get('related_source_ids',[])],
          'review_status':'automated_source_inspection; no independent policy approval',
          'human_reviewed_on':None,'translation_status':'VERA summaries are AI-drafted; official excerpt remains in original language',
          'reuse_status':s['reuse_policy'],'reuse_terms_url':s['reuse_terms_url'],
          'attribution':'Original VERA summary. '+('Short copy from '+doc['title']+' by '+s['publisher']+', version captured at '+c['retrieved_at']+' from '+url+'.' if e else 'See '+doc['title']+' by '+s['publisher']+' at '+url+'.'),
          'checked_on':c['checked_on'],'retrieved_at':c['retrieved_at'],'freshness_days':s['freshness_days'],
          'publisher_modified_on':c.get('publisher_modified_on'),'effective_from':None,'effective_to':None,
          'embedding_model':None,'embedding_revision':None,
          'search_terms':tokens(text+' '+' '.join(s.get('summary',{}).values())+' '+doc['title']+' '+section)})
        if c.get('excerpt_gap'):gaps.append({'document_id':did,'kind':'excerpt_gap','detail':c['excerpt_gap']})
        if not c.get('publisher_modified_on'):gaps.append({'document_id':did,'kind':'publisher_modified_date_unknown'})
    known={c['id'] for c in chunks}
    for chunk in chunks:
        chunk['related_chunk_ids']=[x for x in chunk['related_chunk_ids'] if x in known]
    # Hash content versions and actual indexed text, not a build/capture timestamp.
    version=digest({'aliases':registry['aliases'],'documents':[(d['document_id'],d.get('content_version'),d['status']) for d in documents],
                    'chunks':[(c['id'],c['source_version'],c['text'],c['localized_summary'],c['search_terms']) for c in chunks]})
    result={'schema_version':2,'corpus_version':version,'generated_at':datetime.now(timezone.utc).isoformat(),
      'retrieval_kind':'unicode_lexical_no_embeddings','source_report':str(report_path.relative_to(ROOT) if report_path.is_absolute() else report_path),
      'aliases':registry['aliases'],'documents':documents,'chunks':chunks,
      'coverage':{'registered_sources':len(sources),'attempted_documents':len(documents),'captured_documents':sum(d['status'].startswith('captured') for d in documents),
        'indexed_documents':len({c['document_id'] for c in chunks}),'chunks':len(chunks),
        'official_short_excerpts':sum(bool(c['verbatim_excerpt']) for c in chunks),
        'languages':sorted({c['locale'] for c in chunks}),'topics':sorted({c['topic'] for c in chunks}),
        'human_policy_reviews':0,'human_language_reviews':0,'embedding_model':None},
      'policy_approvals_changed':False,'limitations':['Preparation corpus, not a complete policy/eligibility database.',
        'PDF documents are hashed but not indexed until page-level visual extraction review.',
        'BC and university texts are not republished; only original summaries and links are public.',
        'French summaries are machine drafts, not certified translations or independent reviews.',
        'No benefit amounts, deadlines or personal eligibility decisions are derived from this index.']}
    path=Path(output)
    if path.suffix=='.sqlite':sqlite_output=path;path=ROOT/'data/evidence/index.json'
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    quality={'schema_version':2,'corpus_version':version,'generated_at':result['generated_at'],'coverage':result['coverage'],'gaps':gaps,
      'all_source_hashes_recorded':all(d.get('content_version') for d in documents if d['status'].startswith('captured')),
      'all_chunk_locators_recorded':all(c['locator'] and c['section'] for c in chunks),
      'all_reuse_metadata_recorded':all(c['reuse_status'] and c['reuse_terms_url'] for c in chunks),
      'no_policy_approvals_changed':True}
    (ROOT/'data/evidence/quality-report.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2)+'\n')
    if sqlite_output:
        p=Path(sqlite_output);p.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(p) as db:
            db.execute('DROP TABLE IF EXISTS evidence')
            db.execute('CREATE TABLE evidence (id TEXT PRIMARY KEY, source_id TEXT, version TEXT, topic TEXT, locale TEXT, section TEXT, text TEXT)')
            db.executemany('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',[(c['id'],c['source_id'],c['source_version'],c['topic'],c['locale'],c['section'],c['text']) for c in chunks])
            db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT)')
            db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('corpus_version',version))
    return dict(result['coverage'],index=str(path),corpus_version=version,gaps=len(gaps))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture-report')
    p.add_argument('--output',default='data/evidence/index.json');p.add_argument('--sqlite')
    a=p.parse_args();print(json.dumps(build(a.output,a.capture_report,a.sqlite)))
