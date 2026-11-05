# Run from the VERA folder with .venv activated:  .\capture_sources.ps1
$ErrorActionPreference = "Stop"
python sources.py capture S1 "https://studentaidbc.ca/help-centre/applying-loans/basic-eligibility-requirements"
python sources.py capture S2 "https://www.welcomebc.ca/start-your-life-in-b-c/find-newcomer-services/services-for-newcomers-on-a-temporary-work-or-study-permit-and-new-citizens%C2%A0(bc-nsp)"
python sources.py capture S3 "https://ircc.canada.ca/english/newcomers/services/"
python sources.py capture S4 "https://www.canada.ca/en/immigration-refugees-citizenship/services/settle-canada/newcomer-services/eligibility.html"
python sources.py capture S5 "https://www.canada.ca/en/services/benefits/finder.html"
python sources.py verify
