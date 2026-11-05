# Re-captures only S4 and S5 (S1-S3 already captured and verified). Run with .venv active.
python sources.py capture S4 "https://www.canada.ca/en/immigration-refugees-citizenship/services/settle-canada/newcomer-services/eligibility.html"
python sources.py capture S5 "https://www.canada.ca/en/services/benefits/finder.html"
python sources.py verify
