"""Local Streamlit adapter over the shared VERA core.
Run: python -m streamlit run app.py
For the polished web UI with no dependencies: python run.py
"""
import json
from datetime import date
import streamlit as st
from agent import Navigator
from models import QUESTIONS

st.set_page_config(page_title='VERA · Your next step in BC',page_icon='🌿',layout='centered')
st.markdown('''<style>.stApp{background:#f7f8f3;color:#173d35}.block-container{max-width:860px;padding-top:2.4rem}h1,h2{color:#173d35}div[data-testid="stForm"]{background:white;border:1px solid #dce2d6;border-radius:16px}</style>''',unsafe_allow_html=True)
if 'navigator' not in st.session_state: st.session_state.navigator=Navigator()
n=st.session_state.navigator
st.caption('VERA  /  NEWCOMER SUPPORT IN BRITISH COLUMBIA')
st.title('A clearer path to your next chapter.')
st.write('Official sources, a few relevant questions, and a plan you can make your own.')
st.info('Preparation guidance only. All rules await independent review. No model connection is used by default.')
if st.button('Clear session and start again'):
 st.session_state.clear(); st.rerun()
if not n.facts.goal:
 with st.form('goal'):
  goal=st.text_area('What would you like help with?',max_chars=600,placeholder='I need help settling in and with student funding.')
  if st.form_submit_button('Find my next step'):
   try:n.start(goal);st.rerun()
   except ValueError as e:st.error(str(e))
 st.caption('Use fictional personas for demonstrations. Do not provide names, IDs, addresses or documents.')
 st.stop()
st.caption(n.facts.goal)
q=n.next_question()
if q:
 with st.form('question_'+q['field']):
  key=q['field'];st.subheader(q['question'])
  if key=='status_category': opts=['prefer_not_to_say','study_permit','work_permit','permanent_resident','protected_person','citizen','other']
  elif key=='pr_class':opts=[None,'economic','family','refugee','other']
  elif key=='pr_landing_date':opts=None
  else:opts=['unknown','yes','no']
  answer=st.selectbox('Choose an answer',opts,format_func=lambda v:(v or 'Not sure / skip').replace('_',' ').title()) if opts else st.date_input('PR date (optional)',value=None,max_value=date.today())
  if st.form_submit_button('Save answer'):
   try:n.answer(key,answer.isoformat() if isinstance(answer,date) else answer);st.rerun()
   except ValueError as e:st.error(str(e))
with st.expander('Review or correct your answers'):
 with st.form('correction'):
  field=st.selectbox('Answer to correct',list(QUESTIONS),format_func=lambda f:QUESTIONS[f])
  value=st.text_input('New category value',help='Use the categories shown above (for example yes, no, study_permit). Dates use YYYY-MM-DD. Leave empty to skip.')
  if st.form_submit_button('Apply correction'):
   try:n.answer(field,value or None);st.session_state.pop('enquiry',None);st.rerun()
   except (ValueError,TypeError) as e:st.error(str(e))
for pid,r in n.results.items():
 with st.expander(pid+' · Needs official review'):
  st.write(r.next_action)
  for outcome in r.rule_outcomes:st.caption(outcome.rule_id+': '+outcome.reason)
  st.caption('Draft explanations are not an eligibility decision.')
st.subheader('Your next steps')
for i,t in enumerate(n.plan['tasks']):
 t['done']=st.checkbox('Complete step '+str(i+1),value=t.get('done',False),key=f'task_{n.facts.version}_{i}')
 t['text']=st.text_input('Edit step '+str(i+1),value=t['text'],key=f'task_text_{n.facts.version}_{i}')
 st.link_button('Official source '+t['source_id'],t['url'])
st.subheader('Your provider enquiry')
message=st.text_area('Edit before contacting a provider',value=n.plan['enquiry'],height=330,key='enquiry_'+str(n.facts.version))
n.plan['enquiry']=message
md='# VERA plan\n\nAs of '+n.as_of.isoformat()+'\n\n## Checklist\n'+ '\n'.join(('- [x] ' if t.get('done') else '- [ ] ')+t['text']+'\n  '+t['url'] for t in n.plan['tasks'])+'\n\n## Unsent enquiry\n\n'+message+'\n\n'+n.plan['limits']
st.download_button('Download checklist & enquiry',md,'VERA_Plan.md','text/markdown')
st.download_button('Download source-linked session',json.dumps(n.export(),indent=2),'VERA_Plan.json','application/json')
with st.expander('Actual tool events'):
 st.json(n.events)
with st.expander('Optional model planning (local app only)'):
 st.write('The hosted UI uses no language model. This optional adapter lets a configured model choose among the same bounded tools. Rules and output remain deterministic.')
 consent=st.checkbox('Send my goal, category answers and source summaries to Anthropic for this request.')
 if st.button('Run model-assisted planning',disabled=not consent):
  from model_agent import run_model_plan
  outcome=run_model_plan(n)
  if outcome['error']:st.warning(outcome['error']+' The guided plan above remains available.')
  st.json(outcome['events'])
st.caption('VERA keeps session answers in Streamlit session memory. No transcript files or external submissions are created. Close the session to discard it. Kopal Chaudhary’s inherited prototype remains in baseline/.')
