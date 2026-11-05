VERA — Vehicle & Employment Regulations Assistant
==================================================

REQUIREMENTS
------------
Python 3.10+
An Anthropic API key (set as ANTHROPIC_API_KEY environment variable)
An OpenAI API key (set as OPENAI_API_KEY environment variable — only needed for evaluate.py)

SETUP
-----
1. Install dependencies:
   pip install -r requirements.txt

2. Build the database:
   python ingest.py

HOW TO RUN
----------
Web interface (recommended):
   streamlit run app.py

Terminal chatbot:
   python chatbot.py

ABLATION STUDY (optional)
--------------------------
Build all three databases:
   python ingest.py
   python ingest_fixed.py
   python ingest_paragraph.py

Run the evaluation:
   python evaluate.py
