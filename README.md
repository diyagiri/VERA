# VERA - newcomer support navigator (hackathon prototype)

Helps a newcomer in BC reach a justified next step for three pathways:
STU-01 StudentAid BC, NEW-02 BC Newcomer Services Program, NEW-03 federal settlement services.

**Status:** prototype in progress. No performance results are claimed. Not legal or immigration advice.

## Layout
- `models.py` data contracts | `sources.py` catalog + retrieval | `rules.py` screening
- `agent.py` bounded tool loop | `actions.py` checklist + enquiry | `app.py` Streamlit UI
- `data/` manifest, snapshots, rules, fixtures | `tests/`, `evaluate.py`
- `baseline/` inherited prototype (unchanged) | `docs/` journey, decisions, attribution

## Setup (Windows, from this folder)
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    python -m pytest -q
