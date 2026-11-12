"""Freeze each output once, then score the frozen artifact. No fabricated judges.
python evaluate.py freeze --output reports/frozen_run.json
python evaluate.py score --input reports/frozen_run.json --output reports/evaluation.json
"""
from __future__ import annotations
from pathlib import Path
from datetime import date,datetime,timezone
import argparse,hashlib,json,math,platform,statistics,time
from agent import Navigator
from models import facts_from_dict,to_dict
from rules import check_all
ROOT=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(output):
 if output.exists():raise ValueError('Frozen outputs already exist. Choose a new filename to preserve the experiment.')
 cases=json.loads((ROOT/'data/fixtures/screening_cases.json').read_text(encoding='utf-8'))['cases']
 journeys=json.loads((ROOT/'data/fixtures/journeys.json').read_text(encoding='utf-8'))['journeys']
 case_outputs=[];journey_outputs=[]
 for c in cases:
  f=facts_from_dict(c['facts']);asof=date.fromisoformat(c['as_of_date'])
  start=time.perf_counter();draft=check_all(f,asof,allow_draft=True);live=check_all(f,asof)
  case_outputs.append({'id':c['case_id'],'split':c['split'],'expected':c['expected'],'expected_missing':c.get('expected_missing',{}),'draft':{k:to_dict(v) for k,v in draft.items()},'live':{k:to_dict(v) for k,v in live.items()},'duration_ms':(time.perf_counter()-start)*1000})
 for j in journeys:
  start=time.perf_counter();n=Navigator(as_of=date(2026,11,11)).start(j['goal'])
  for field,value in j['answers']:n.answer(field,value)
  nextq=n.next_question();duration=(time.perf_counter()-start)*1000
  journey_outputs.append({'id':j['id'],'split':j['split'],'expected':j['expected'],'output':n.export(),'next':nextq['field'] if nextq else None,'duration_ms':duration,'answer_actions':len(j['answers'])})
 payload={'run_at_utc':datetime.now(timezone.utc).isoformat(),'python':platform.python_version(),'model':'none — deterministic guided workflow','cost_usd':0,'cost_scope':'Model API calls only; hosting/development costs not measured.','source_files':{f:digest(ROOT/f) for f in ['rules.py','agent.py','actions.py','sources.py','model_agent.py','data/manifest.json','web/engine.js','scripts/build_web.py','data/rules/rules.json','data/evidence.json','data/fixtures/screening_cases.json','data/fixtures/journeys.json']},'cases':case_outputs,'journeys':journey_outputs}
 output.parent.mkdir(exist_ok=True,parents=True);output.write_text(json.dumps(payload,indent=2)+'\n')
 return {'frozen':str(output),'sha256':digest(output)}

def score(input_path,output):
 if not input_path.exists():raise ValueError('Frozen outputs are missing. Run freeze first.')
 d=json.loads(input_path.read_text(encoding='utf-8'))
 if not isinstance(d.get('cases'),list) or not d['cases'] or not isinstance(d.get('journeys'),list) or not d['journeys']:raise ValueError('Malformed or empty frozen outputs; not a zero score.')
 report={'frozen_sha256':digest(input_path),'run_at_utc':d['run_at_utc'],'model':d['model'],'cases':{},'journeys':{},'limitations':['Synthetic author-written cases; held-out partition is not independently validated and was inspected during routing debugging. This rerun is regression evidence.','Policy correctness and excerpt support still need independent human review.','Full source snapshots are verified locally but excluded from redistribution pending reuse review.','Manual navigation and retrieval-chatbot comparison not performed.','No usability participants; no claim about reduced user effort.','Latency measures local Python orchestration, not human completion or hosted browser time.','No live model-provider request was tested.'],'comparisons':{'manual_navigation':'not_run','retrieval_chatbot':'not_run'},'model_cost_usd':0}
 for split in ['dev','heldout']:
  rows=[c for c in d['cases'] if c['split']==split];failures=[]
  for c in rows:
   for pid,expected in c['expected'].items():
    actual=c['draft'][pid]
    if actual['state']!=expected or (pid in c['expected_missing'] and actual['missing_inputs']!=c['expected_missing'][pid]):failures.append(c['id']+':'+pid)
  report['cases'][split]={'passed':len(rows)-len({x.split(':')[0] for x in failures}),'total':len(rows),'failures':failures}
  journeys=[j for j in d['journeys'] if j['split']==split];jfail=[]
  for j in journeys:
   e=j['expected'];p=j['output']['plan']
   ok=len(p['tasks'])==e['task_count'] and j['next']==e['next'] and all(r['state']=='needs_official_review' for r in j['output']['results'].values())
   if 'enquiry_contains' in e:ok &= e['enquiry_contains'] in p['enquiry']
   if 'enquiry_excludes' in e:ok &= e['enquiry_excludes'] not in p['enquiry']
   if not ok:jfail.append(j['id'])
  report['journeys'][split]={'passed':len(journeys)-len(jfail),'total':len(journeys),'failures':jfail}
 live=[r for c in d['cases'] for r in c['live'].values()]
 report['unsupported_positive_recommendations']={'observed':sum(r['state']=='no_blocker_in_checked_criteria' for r in live),'screens':len(live),'scope':'Gated release mode; zero does not measure policy accuracy or population risk.'}
 durations=sorted(j['duration_ms'] for j in d['journeys'])
 report['latency_ms']={'n':len(durations),'p50':round(statistics.median(durations),3),'p95':round(durations[math.ceil(.95*len(durations))-1],3)}
 output.parent.mkdir(exist_ok=True,parents=True);output.write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','score']);parser.add_argument('--input',type=Path);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
 try:
  result=freeze(a.output) if a.stage=='freeze' else score(a.input or Path('reports/frozen_run.json'),a.output)
  print(json.dumps(result,indent=2))
 except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:parser.exit(2,f'Evaluation error: {e}\n')
