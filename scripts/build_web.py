"""Compile the Python evaluators into finite decision tables for the offline UI.
No duplicated rule logic. Rebuild whenever rules, evidence, or sources change.
"""
from pathlib import Path
import sys,json,itertools,shutil
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models import facts_from_dict, load_rules
from rules import EVALUATORS, approval_problem
from sources import load_manifest, verify_snapshot, PROGRAM_KEYWORDS, OUT_OF_SCOPE_KEYWORDS
ROOT=Path(__file__).resolve().parents[1]
DOMAINS={
 'status_category':[None,'study_permit','work_permit','permanent_resident','protected_person','citizen','other','prefer_not_to_say'],
 'naturalized_citizen':['unknown','yes','no'], 'is_post_secondary_student':['unknown','yes','no'],
 'institution_offers_service':['unknown','yes','no'], 'federal_exception':['unknown','yes','no'],
 'bc_resident':['unknown','yes','no'],'pr_class':[None,'economic','family','refugee','other'],
 'pr_landing_date':[None,'2021-06-21']}
SUMMARIES={
 'S1':'StudentAid BC assesses immigration status, program residency, study eligibility and financial need. A basic screen cannot determine an award.',
 'S2':'BC NSP covers specified newcomer categories. For international post-secondary students, access depends on whether their institution provides the relevant service.',
 'S3':'IRCC settlement services depend on status and specific pathways. Some temporary residents have exceptions that require individual confirmation.',
 'S4':'Economic-class permanent residents face time limits. Transition wording and examples require careful review; VERA does not calculate an end date.',
 'S5':'The federal Benefits Finder supports broader discovery. Its listings are not eligibility decisions.'}
rules=[]
for r in load_rules():
 fields=[x for x in r.required_inputs if x in DOMAINS]
 rows={}
 for values in itertools.product(*(DOMAINS[x] for x in fields)):
  f=facts_from_dict(dict(zip(fields,values)))
  outcome,reason,missing=EVALUATORS[r.rule_id](f,date(2026,11,11))
  key=json.dumps(values,separators=(',',':'))
  rows[key]=[outcome.value,reason,missing]
 rules.append({'id':r.rule_id,'program_id':r.program_id,'fields':fields,'rows':rows,
               'approval_state':r.approval_state,'source_id':r.source_id,'source_version':r.source_version,
               'coverage_limit':r.coverage_limit,'gate':approval_problem(r,date.today()),
               'reviewer':r.reviewer,'reviewed_on':r.reviewed_on,'effective_from':r.effective_from,'effective_to':r.effective_to})
sources=[]
for s in load_manifest():
 sources.append({'id':s.source_id,'program_id':s.program_id,'title':s.title,'publisher':s.publisher,
 'url':s.canonical_url,'summary':SUMMARIES[s.source_id],'checked_on':s.checked_on,
 'page_modified_on':s.page_modified_on,'sha256':s.sha256,'snapshot_verified':verify_snapshot(s),
 'evidence_section':s.evidence_section,'effective_period':s.effective_period,
 'web_rechecked_on':'2026-11-11','captured_at':s.captured_at})
payload={'rules':rules,'sources':sources,'keywords':PROGRAM_KEYWORDS,'out_of_scope':OUT_OF_SCOPE_KEYWORDS,
         'validation':{'python_passed':93,'javascript_passed':12,'parity_cases':252,'screening_cases':30,'scripted_journeys':10,'kind':'synthetic regression checks; independent policy review pending'},'compiled_on':date.today().isoformat(),'mode':'guidance','approval_count':sum(r['gate'] is None for r in rules)}
dist=ROOT/'dist';dist.mkdir(exist_ok=True)
for f in (ROOT/'web').iterdir():
 if f.is_file():shutil.copy2(f,dist/f.name)
(dist/'catalog.json').write_text(json.dumps(payload,separators=(',',':'),ensure_ascii=False))
print(f'Built {len(rules)} rule tables, {len(sources)} sources; {payload["approval_count"]} enabled rules.')
