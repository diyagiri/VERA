"""Run screening fixtures against the rules engine (draft logic visible).

    python tests/fixture_runner.py dev
    python tests/fixture_runner.py heldout   # held-out: run only for evaluation, never tune to it
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import models as m  # noqa: E402
import rules as r  # noqa: E402

CASES_PATH = ROOT / "data/fixtures/screening_cases.json"


def load_cases(split: str | None = None) -> list[dict]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    return [c for c in cases if split is None or c["split"] == split]


def run_case(case: dict) -> dict:
    facts = m.facts_from_dict(case["facts"])
    res = r.check_all(facts, date.fromisoformat(case["as_of_date"]), allow_draft=True)
    out = {}
    for prog, exp_state in case["expected"].items():
        actual = res[prog].state.value
        exp_missing = case.get("expected_missing", {}).get(prog)
        missing_ok = exp_missing is None or res[prog].missing_inputs == exp_missing
        out[prog] = {"expected": exp_state, "actual": actual,
                     "expected_missing": exp_missing, "actual_missing": res[prog].missing_inputs,
                     "missing_ok": missing_ok, "pass": actual == exp_state and missing_ok}
    return out


def summarise(split: str) -> tuple[int, int]:
    cases = load_cases(split)
    passed, failures = 0, []
    for c in cases:
        out = run_case(c)
        if all(v["pass"] for v in out.values()):
            passed += 1
        else:
            for prog, v in out.items():
                if not v["pass"]:
                    failures.append(f"  {c['case_id']} {prog}: expected {v['expected']} "
                                    f"{v['expected_missing'] or ''}, got {v['actual']} {v['actual_missing'] or ''}")
    print(f"{split}: {passed}/{len(cases)} cases passed")
    print("\n".join(failures))
    return passed, len(cases)


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if split not in {"dev", "heldout"}:
        print("usage: python tests/fixture_runner.py dev|heldout")
        sys.exit(2)
    p, n = summarise(split)
    sys.exit(0 if p == n else 1)
