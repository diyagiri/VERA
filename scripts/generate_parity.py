from pathlib import Path
import itertools,json,sys
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from models import facts_from_dict,load_rules,to_dict
from rules import EVALUATORS
# Exhaust all individual rule input combinations, including both date presence states.
DOMAINS={'status_category':[None,'study_permit','work_permit','permanent_resident','protected_person','citizen','other','prefer_not_to_say'],'naturalized_citizen':['unknown','yes','no'],'is_post_secondary_student':['unknown','yes','no'],'institution_offers_service':['unknown','yes','no'],'federal_exception':['unknown','yes','no'],'bc_resident':['unknown','yes','no'],'pr_class':[None,'economic','family','refugee','other'],'pr_landing_date':[None,'2021-06-21']}
rows=[]
for rule in load_rules():
 fields=[f for f in rule.required_inputs if f in DOMAINS]
 for values in itertools.product(*(DOMAINS[f] for f in fields)):
  facts=facts_from_dict(dict(zip(fields,values)))
  out,reason,missing=EVALUATORS[rule.rule_id](facts,date(2026,11,11))
  rows.append({'rule_id':rule.rule_id,'facts':to_dict(facts),'expected':{'outcome':out.value,'reason':reason,'missing':missing}})
Path('data/fixtures/web_parity.json').write_text(json.dumps(rows,separators=(',',':'))+'\n')
print(f'{len(rows)} cross-runtime parity cases generated (not independent policy validation).')
