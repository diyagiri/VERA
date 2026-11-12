"""Restore exact expected source bytes without changing approved metadata.
A changed response is a review event, never a silent version update.
"""
from pathlib import Path
import sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sources import load_manifest,_fetch,verify_snapshot,ROOT
bad=[]
for src in load_manifest():
 if verify_snapshot(src):print(src.source_id+': already verified');continue
 try:
  body=_fetch(src.canonical_url,retries=1)
  if hashlib.sha256(body).hexdigest()!=src.sha256:raise ValueError('Source bytes changed; capture and review a new version explicitly.')
  path=ROOT/src.snapshot_path;path.parent.mkdir(exist_ok=True,parents=True);path.write_bytes(body)
  print(src.source_id+': exact snapshot restored')
 except Exception as e:
  bad.append(src.source_id);print(src.source_id+': unavailable or changed ('+type(e).__name__+'). Screening remains gated.')
sys.exit(bool(bad))
