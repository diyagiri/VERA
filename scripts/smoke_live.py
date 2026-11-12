"""Explicit live-provider check using fictional input; never records raw prompts or keys."""
import asyncio,json,sys,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from settings import Settings
from sessions import Session
from conversation import converse,Budget
from api_contracts import Message
from catalog import load_catalog

async def run(output):
    settings=Settings.from_env()
    result={'schema_version':2,'test':'live_provider','status':'blocked','model':settings.model or None}
    if not settings.online:
        result['reason']='ANTHROPIC_API_KEY and VERA_MODEL are required; no provider request was made.'
    else:
        session=Session(True,'en')
        session.profile={'facts':{'province':{'value':'BC','state':'confirmed','version':1,'confirmed_at':None}},'goals':['banking','taxes'],'priority':'banking'}
        request=Message(message='I just moved to BC for work. How should I get ready to choose a bank account and understand newcomer taxes?',locale='en',profile_version=0,plan_version=0,idempotency_key='live_smoke_fictional_01')
        try:
            turn=await converse(settings,session,request,load_catalog(),Budget())
            result.update(status='passed',model=turn['model'],duration_ms=turn['duration_ms'],usage=turn['usage'],events=turn['events'],citation_count=len(turn['citations']))
        except Exception as exc:result.update(status='failed',error_type=type(exc).__name__)
    path=Path(output)
    if path.exists():raise ValueError('Choose a new output path; do not overwrite a measured run.')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if result['status']=='passed' else 2
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();sys.exit(asyncio.run(run(a.output)))
