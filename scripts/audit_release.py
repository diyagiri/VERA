from pathlib import Path
from datetime import date
import sys,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sources import load_manifest,verify_snapshot
from rules import approval_problem,load_rules
p=argparse.ArgumentParser();p.add_argument('--require-screening',action='store_true');a=p.parse_args()
rules=[{'id':r.rule_id,'blocker':approval_problem(r,date.today())} for r in load_rules()]
report={'guidance_mode_ready':True,'live_screening_ready':all(r['blocker'] is None for r in rules),'sources':[{'id':s.source_id,'snapshot_verified':verify_snapshot(s)} for s in load_manifest()],'rules':rules,'external_gates':['Independent rule and evidence sign-off','Source snapshot restoration / exact version verification','Event rubric and pre-existing-code policy confirmation','Source reuse review before redistribution','Live model credentials and provider smoke test if enabled']}
print(json.dumps(report,indent=2))
sys.exit(1 if a.require_screening and not report['live_screening_ready'] else 0)
