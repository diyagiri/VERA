"""Run meaningful checks and generate release metrics from their actual results."""
import hashlib,json,re,subprocess,sys,tempfile,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]

def run(args):
    r=subprocess.run(args,cwd=ROOT,text=True,capture_output=True)
    if r.returncode:
        print(r.stdout);print(r.stderr,file=sys.stderr);raise SystemExit(r.returncode)
    return r.stdout

if __name__=='__main__':
    run(['npm','run','build'])
    with tempfile.TemporaryDirectory() as tmp:
        xml=Path(tmp)/'pytest.xml'
        run([sys.executable,'-m','pytest','-q','--junitxml='+str(xml)])
        suites=ET.parse(xml).getroot().findall('testsuite')
        totals={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    js=run(['node','--test','--test-reporter=tap',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('*.test.mjs'))]])
    stats={k:int(re.search(r'^# '+k+r' (\d+)$',js,re.M).group(1)) for k in ['tests','pass','fail','skipped']}
    audit=json.loads(run([sys.executable,'scripts/audit_release.py']))
    digest=hashlib.sha256()
    inputs=[]
    for folder in ['', 'web','worker','data/catalog','data/evidence','tests']:
        paths=ROOT.glob('*.py') if not folder else (ROOT/folder).rglob('*')
        for p in sorted(paths):
            if p.is_file() and p.suffix in {'.py','.js','.mjs','.json','.css','.html'}:
                rel=str(p.relative_to(ROOT));inputs.append(rel);digest.update(rel.encode());digest.update(p.read_bytes())
    result={'schema_version':2,'measured_at':datetime.now(timezone.utc).isoformat(),
        'kind':'functional regression checks; no independent policy or language validation',
        'baseline_reviewed_commit':'185e545eb77c0c501d16673318d2bba56f278988',
        'source_input_sha256':digest.hexdigest(),'input_count':len(inputs),
        'python':dict(totals,passed=totals['tests']-totals['failures']-totals['errors']-totals['skipped']),
        'javascript':stats,'live_screening_ready':audit['live_screening_ready'],
        'live_provider_report':'v3_live_provider_01.json',
        'retrieval_report':'v2_development_01.json',
        'browser_report':'v3_browser_01.json',
        'human_language_reviewed':False,'policy_reviewed':False}
    (ROOT/'reports/verification_latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
