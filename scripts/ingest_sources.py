"""Capture allowlisted official source bytes for review, without approving or publishing them.
Full captures are ignored by Git and excluded from portable archives.
"""
import argparse, hashlib, json, sys, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import load_catalog, ROOT

ALLOWED={'www.canada.ca','ircc.canada.ca','www.welcomebc.ca','studentaidbc.ca','www.sfu.ca','students.ubc.ca'}
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme!='https' or urllib.parse.urlparse(newurl).hostname not in ALLOWED:
            raise ValueError('Redirect outside official allowlist')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def capture(source):
    url=source['url']
    if urllib.parse.urlparse(url).scheme!='https' or urllib.parse.urlparse(url).hostname not in ALLOWED:
        raise ValueError('Source is not allowlisted')
    req=urllib.request.Request(url,headers={'User-Agent':'VERA-source-review/2.0'})
    with urllib.request.build_opener(SafeRedirect).open(req,timeout=20) as response:
        content=response.read(15_000_001)
        if len(content)>15_000_000:raise ValueError('Document exceeds capture limit')
        sha=hashlib.sha256(content).hexdigest()
        folder=ROOT/'data/snapshots/v2';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(source['id']+'-'+sha[:16]+'.capture')
        if not path.exists():path.write_bytes(content)
        return {'id':source['id'],'original_url':url,'resolved_url':response.url,
                'retrieved_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':sha,
                'content_type':response.headers.get('Content-Type'),'publisher_last_modified':response.headers.get('Last-Modified'),
                'path':str(path.relative_to(ROOT)),'status':'captured_pending_extraction_and_review',
                'human_reviewed_on':None,'reuse_status':'not_cleared_for_redistribution'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ids',nargs='+',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    sources={s['id']:s for s in load_catalog()['sources']}
    if set(args.ids)-sources.keys():parser.error('Only known source IDs are accepted')
    results=[]
    for sid in args.ids:
        try:results.append(capture(sources[sid]))
        except Exception as exc:results.append({'id':sid,'status':'failed','error_type':type(exc).__name__})
    output=Path(args.output)
    if output.exists():parser.error('Use a new report path; capture history is immutable')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'schema_version':2,'captures':results,'policy_approvals_changed':False},indent=2)+'\n')
    print(json.dumps({'captured':sum(x['status'].startswith('captured') for x in results),'failed':sum(x['status']=='failed' for x in results),'report':str(output)}))
    sys.exit(1 if any(x['status']=='failed' for x in results) else 0)
