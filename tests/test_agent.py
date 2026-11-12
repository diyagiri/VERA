from datetime import date
import pytest
from agent import Navigator,MAX_CALLS
from models import TriState,StatusCategory,load_rules
from rules import approval_problem,new03_r1
from model_agent import run_model_plan


def journey():
 n=Navigator(as_of=date(2026,11,11)).start('I want help settling in and student funding.')
 for k,v in [('bc_resident','yes'),('status_category','study_permit'),('is_post_secondary_student','yes'),('institution_offers_service','no'),('federal_exception','unknown')]:n.answer(k,v)
 return n


def test_session_complete_with_skipped_exception_and_official_handoffs():
 n=journey()
 assert n.next_question() is None
 assert all(r.state.value=='needs_official_review' for r in n.results.values())
 assert n.plan['tasks'] and 'institution does not offer' in n.plan['enquiry']
 assert all(t['url'].startswith('https://') for t in n.plan['tasks'])
 assert {e['tool'] for e in n.events}>={'search_sources','check_rules','prepare_plan'}


def test_correction_invalidates_context_and_only_rechecks_dependents():
 n=journey();old=n.results['STU-01'];n.answer('institution_offers_service','yes')
 assert 'institution does not offer' not in n.plan['enquiry']
 assert n.results['STU-01'] is old
 assert [c['program_id'] for c in n.changes]==['NEW-02']
 assert 'institution' in n.plan['tasks'][0]['text']


def test_status_correction_clears_obsolete_conditional_answers():
 n=journey();n.answer('status_category','permanent_resident')
 assert n.facts.institution_offers_service==TriState.UNKNOWN
 assert n.facts.pr_class is None
 assert 'study permit' not in n.plan['enquiry']
 assert 'post-secondary student' not in n.plan['enquiry']
 assert n.next_question()['field']=='pr_class'


def test_unknown_federal_exception_never_becomes_exclusion():
 n=journey()
 assert new03_r1(n.facts,n.as_of)[0].value=='unknown'
 n.answer('federal_exception','yes')
 assert new03_r1(n.facts,n.as_of)[0].value=='review_required'
 n.answer('federal_exception','no')
 assert new03_r1(n.facts,n.as_of)[0].value=='fail'


def test_skip_prevents_repeated_question():
 n=Navigator().start('settlement services')
 n.answer('bc_resident','unknown');n.answer('status_category','prefer_not_to_say')
 assert n.next_question() is None


def test_out_of_scope_does_not_ask_status():
 n=Navigator().start('help with rent and dental benefits')
 assert n.next_question() is None
 assert n.results=={}
 assert n.plan['tasks'][0]['source_id']=='S5'


def test_future_date_invalid_and_unknown_fields_rejected():
 n=journey()
 with pytest.raises(ValueError):n.answer('sin_number','000000000')
 with pytest.raises(ValueError):n.answer('pr_landing_date','2099-01-01')
 with pytest.raises(ValueError):n.answer('status_category','administrator')
 with pytest.raises(ValueError):n.answer('pr_class','invented')


def test_call_budget_and_event_cap():
 n=journey();n._calls=MAX_CALLS
 with pytest.raises(RuntimeError):n._call('check_rules','test',lambda:None)
 for i in range(40):n.answer('institution_offers_service','no' if i%2 else 'yes')
 assert len(n.events)<=80


def test_unreviewed_rule_cannot_be_enabled_and_self_approval_rejected():
 r=load_rules()[0]
 assert 'awaiting' in approval_problem(r,date(2026,11,11))
 r.approval_state='RULE_APPROVED';r.reviewer=r.author
 assert 'Independent reviewer' in approval_problem(r,date(2026,11,11))
 r.reviewer='Test independent reviewer';r.reviewed_on='2026-11-11';r.test_ids=['synthetic'];r.coverage_limit='Status only'
 r.source_version='0'*64
 assert 'unavailable' in approval_problem(r,date(2026,11,11))


def test_model_unknown_tools_and_repetitions_fall_back():
 n=journey()
 bad=lambda *_:{'content':[{'type':'tool_use','id':'1','name':'send_email','input':{}}]}
 out=run_model_plan(n,request=bad)
 assert out['error'] and out['plan']==n.plan
 repeat=lambda *_:{'content':[{'type':'tool_use','id':'1','name':'search_sources','input':{'goal':'test'}}]}
 out=run_model_plan(n,request=repeat)
 assert out['error'] and len(out['events'])==1


def test_model_preparation_uses_deterministic_plan():
 n=journey()
 request=lambda *_:{'content':[{'type':'tool_use','id':'1','name':'prepare_plan','input':{}}]}
 out=run_model_plan(n,request=request)
 assert out['error'] is None and out['plan']==n.plan
