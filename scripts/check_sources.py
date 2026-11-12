"""Report source freshness and metadata gaps. Never auto-approve policy rules."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog import load_catalog,source_current,bc_today

def check(as_of=None):
    c=load_catalog();as_of=as_of or bc_today();results=[]
    for s in c['sources']:
        missing=[k for k in ['id','publisher','url','resolved_url','section','checked_on','version','reuse_status'] if not s.get(k)]
        results.append({'id':s['id'],'current':source_current(s,as_of),'missing_metadata':missing,
                        'human_reviewed':bool(s.get('human_reviewed_on')),'full_snapshot_available':bool(s.get('snapshot_sha256'))})
    return {'schema_version':2,'as_of':as_of,'source_count':len(results),'sources':results,
            'network_recheck_performed':False,'screening_enabled':False,
            'note':'Catalog age/version check only. A successful build does not re-inspect publishers.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');p.add_argument('--as-of');a=p.parse_args();r=check(a.as_of)
    if a.output:Path(a.output).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
