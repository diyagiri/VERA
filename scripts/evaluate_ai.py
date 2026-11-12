"""Small live test of the AI assistant (needs ANTHROPIC_API_KEY in .env and requirements-api.txt).

Sends each fictional goal in data/fixtures/ai_quality_cases.json through the real local API,
records what Claude proposed and wrote, and scores:
  1. facts: proposed facts that match what the message states, and facts it should not have proposed
  2. citations: every cited chunk was retrieved (structural); semantic support is judged by a reviewer
     from the evidence text saved in the raw report
  3. eligibility claims in the text the person sees
Writes reports/ai_quality_raw.json. Never prints or saves the key. Run from the repository root:
    python scripts/evaluate_ai.py
"""
import json, re, sys, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
from server import create_app
from settings import Settings

CLAIM = re.compile(r"\byou(?:'re| are)? (?:are )?(?:eligible|qualify|qualified|approved|will (?:receive|get|be approved))"
                   r"|\bvous (?:êtes (?:admissible|approuvée?s?)|recevrez|avez droit|êtes éligible)", re.I)
LEAD = re.compile(r"(?:whether|if|to see if|to check if|ask|si)\s+$", re.I)
REFUSAL = re.compile(r"(?:can't|cannot|won't|will not|not able to|ne peux pas|ne pas)\b[^.!?]{0,30}$", re.I)  # "I can't tell you that you're approved"

def claims(text):
    return [m.group(0) for m in CLAIM.finditer(text) if not LEAD.search(text[max(0, m.start() - 20):m.start()]) and not REFUSAL.search(text[max(0, m.start() - 40):m.start()])]

def main():
    settings = Settings.from_env()
    if not settings.online:
        sys.exit('ANTHROPIC_API_KEY or VERA_MODEL missing from .env')
    cases = json.loads((ROOT / 'data/fixtures/ai_quality_cases.json').read_text(encoding='utf-8'))['cases']
    only = set(sys.argv[1:])
    results = []
    for case in cases:
        if only and case['id'] not in only:
            continue
        client = TestClient(create_app(settings), base_url=settings.origin,  # fresh app = fresh session and budget per case
                            headers={'origin': settings.origin, 'x-vera-client': 'browser-v2'})
        s = client.post('/api/v1/sessions', json={'consent': True, 'locale': case['locale']}).json()
        t0 = time.monotonic()
        r = client.post('/api/v1/sessions/current/messages', json={
            'message': case['message'], 'locale': case['locale'], 'idempotency_key': uuid.uuid4().hex,
            'profile_version': s['profile_version'], 'plan_version': s['plan_version']}).json()
        seconds = round(time.monotonic() - t0, 1)
        row = {'id': case['id'], 'locale': case['locale'], 'style': case['style'], 'message': case['message'], 'seconds': seconds}
        if 'turn' not in r:
            row['error'] = (r.get('error') or {}).get('code') or r.get('detail') or 'unknown'
            print(f"{case['id']}: ERROR {row['error']} ({seconds}s)")
            results.append(row); continue
        turn = r['turn']
        proposed = {f['field']: f['value'] for f in turn['proposed_facts']}
        exp = case['expected']
        right = sorted(k for k, v in exp.items() if proposed.get(k) == v)
        missed = sorted(k for k in exp if k not in proposed)
        wrong = sorted(k for k, v in proposed.items() if k in exp and v != exp[k] and v not in ('unknown', 'declined'))
        forbidden = sorted(k for k, v in proposed.items() if k in case['must_not'] and v not in ('unknown', 'declined'))
        extra = sorted(k for k, v in proposed.items() if k not in exp and k not in case['must_not'] and v not in ('unknown', 'declined'))
        evidence = {c['id']: c for c in turn['citations']}
        shown = [b['text'] for b in turn['blocks']] + turn['questions']
        row.update(
            topics=turn['topics'], proposed_facts=proposed,
            facts={'expected': len(exp), 'right': right, 'missed': missed, 'wrong': wrong, 'forbidden': forbidden, 'extra': extra},
            blocks=[{'text': b['text'], 'citations': b['citations'],
                     'evidence': {cid: (evidence[cid].get('display_text') if cid in evidence else None) for cid in b['citations']}}
                    for b in turn['blocks']],
            questions=turn['questions'], program_ids=turn['program_ids'],
            citations_retrieved=all(cid in evidence for b in turn['blocks'] for cid in b['citations']),
            eligibility_claims=[c for t in shown for c in claims(t)],
            retries=sum(1 for e in turn['events'] if e.get('status') == 'retry'),
            usage=turn['usage'], model=turn['model'])
        print(f"{case['id']}: facts {len(right)}/{len(exp)} right, wrong {wrong or '-'}, not allowed {forbidden or '-'}, "
              f"extra {extra or '-'}; claims {len(row['eligibility_claims'])}; retries {row['retries']}; {seconds}s")
        results.append(row)
    out = ROOT / 'reports/ai_quality_raw.json'
    if only and out.exists():  # rerun of some cases: keep the others
        old = {x['id']: x for x in json.loads(out.read_text(encoding='utf-8'))['results']}
        old.update({x['id']: x for x in results}); results = [old[k] for k in sorted(old)]
    out.write_text(json.dumps({'run_on': time.strftime('%Y-%m-%d'), 'model': settings.model, 'results': results},
                              ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved', out.relative_to(ROOT))

if __name__ == '__main__':
    main()
