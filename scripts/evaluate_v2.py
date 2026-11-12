"""Reproducible development/regression retrieval and Python/browser parity checks."""
import argparse, json, hashlib, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import load_catalog, ROOT, bc_today
from retrieval import search_knowledge
from planning import build_plan

def evaluate():
    c=load_catalog();cases=json.loads((ROOT/'data/fixtures/v2/retrieval_cases.json').read_text());rows=[]
    for case in cases:
        got=[chunk['source_id'] for chunk in search_knowledge(c,case['query'],[case['topic']],case['locale'],5)]
        rows.append(dict(case_id=case['id'],locale=case['locale'],topic=case['topic'],expected=case['expected'],retrieved=got,recall=sum(s in got for s in case['expected'])/len(case['expected'])))
    aggregates={lang:{'cases':sum(r['locale']==lang for r in rows),'recall_at_5':sum(r['recall'] for r in rows if r['locale']==lang)/sum(r['locale']==lang for r in rows)} for lang in ['en','fr']}
    profiles=[]
    for institution in ['sfu','ubc_vancouver','ubc_okanagan','other','unknown']:
        for service in ['yes','no','unknown']:
            for locale in ['en','fr']:
                facts={k:{'value':v,'state':'unknown' if v=='unknown' else 'confirmed','version':1,'confirmed_at':None} for k,v in {'province':'BC','institution':institution,'institution_service':service,'children':'yes'}.items()}
                profiles.append({'profile':{'facts':facts,'goals':['settlement','education','banking','taxes','benefits'],'priority':'banking'},'locale':locale})
    expected=[build_plan(c,p['profile'],p['locale'],as_of=bc_today()) for p in profiles]
    script="import fs from 'node:fs';import {buildPlan} from './web/navigator.js';const input=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(input.profiles.map(p=>buildPlan(input.catalog,p.profile,p.locale,null,0,input.day))));"
    actual=json.loads(subprocess.run(['node','--input-type=module','-e',script],input=json.dumps({'catalog':c,'profiles':profiles,'day':bc_today()}),text=True,capture_output=True,check=True,cwd=ROOT).stdout)
    matches=[a==b for a,b in zip(expected,actual)]
    return {'schema_version':2,'created_at':datetime.now(timezone.utc).isoformat(),'as_of':bc_today(),
            'kind':'author-written development/regression cases; not held-out or independent policy evaluation',
            'retrieval_method':'Unicode lexical ranking of curated bilingual summaries with user-selected topic filter; no embeddings',
            'catalog_sha256':hashlib.sha256((ROOT/'data/catalog/navigation.json').read_bytes()).hexdigest(),
            'retrieval':aggregates,'retrieval_cases':rows,'python_browser_parity':{'cases':len(matches),'passed':sum(matches)},
            'live_provider_evaluated':False,'human_language_reviewed':False,'policy_reviewed':False,
            'passed':all(r['recall']==1 for r in rows) and all(matches)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();path=Path(a.output)
    if path.exists():p.error('Choose a new output file; keep previous measured reports')
    result=evaluate();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['retrieval','python_browser_parity','passed']}));sys.exit(0 if result['passed'] else 1)
