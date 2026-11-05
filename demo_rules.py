"""Print a persona's screening journey in the terminal. No LLM.

    python demo_rules.py P1-MEI            # draft logic shown (allow_draft)
    python demo_rules.py P1-MEI --gated    # what live screening shows today
"""
import json
import sys
from datetime import date
from pathlib import Path

import models as m
import rules as r

LABEL = {"blocker_found": "Blocker found", "no_blocker_in_checked_criteria": "No blocker in checked criteria",
         "needs_information": "Needs information", "needs_official_review": "Needs official review"}


def show(results, title):
    print(f"\n=== {title}")
    for pid, res in results.items():
        print(f"{pid:7} {LABEL[res.state.value]:32} facts v{res.fact_version}")
        for x in res.rule_outcomes:
            print(f"   {x.rule_id:10} {x.outcome.value:16} {x.reason}")
        if res.missing_inputs:
            print(f"   ask: {', '.join(res.missing_inputs)}")


def main(argv):
    pid = argv[0] if argv else "P1-MEI"
    allow = "--gated" not in argv
    p = {x["persona_id"]: x for x in json.loads(Path("data/fixtures/personas.json").read_text(encoding="utf-8"))["personas"]}[pid]
    facts, as_of = m.facts_from_dict(p["facts"], p["goal"]), date.fromisoformat(p["as_of_date"])
    print(f"{pid}: {p['description']}\nGoal: {p['goal']}\nMode: {'draft logic' if allow else 'gated (live)'}")
    res = r.check_all(facts, as_of, allow_draft=allow)
    show(res, "Initial screening")
    c = p.get("correction")
    if c:
        facts.update(c["field"], m.TriState(c["new_value"]))
        res, changed = r.rerun_affected(res, facts, c["field"], as_of, allow_draft=allow)
        show(res, f"After correcting {c['field']} -> {c['new_value']}  (changed: {changed or 'none'})")


if __name__ == "__main__":
    main(sys.argv[1:])
