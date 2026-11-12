"""Create the portable source project. Exclude identity, secrets and raw snapshots."""
from pathlib import Path
import zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist/VERA_Complete_Project.zip'
excluded={'.git','.openai','.venv','venv','node_modules','__pycache__','.pytest_cache','.sites-runtime'}
files=[]
for path in sorted(ROOT.rglob('*')):
 rel=path.relative_to(ROOT)
 if not path.is_file() or any(part in excluded for part in rel.parts):continue
 if str(rel).startswith('data/snapshots/') or path.suffix in {'.zip','.pyc','.tar','.gz','.log','.sqlite'}:continue
 if path.name=='.env' or path.name=='secrets.toml':continue
 files.append(path)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:z.write(p,'VERA/'+p.relative_to(ROOT).as_posix())
print(json.dumps({'path':str(out),'files':len(files),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
