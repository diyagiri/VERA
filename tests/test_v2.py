import asyncio, copy, json, time
import pytest
from fastapi.testclient import TestClient
from api_contracts import Profile, PortablePlan, Message
from catalog import load_catalog, available_programs
from planning import build_plan, validate_import
from retrieval import search_knowledge
from grounding import validate_turn
from server import create_app
from settings import Settings
from sessions import Session
from conversation import converse, Budget, ProviderUnavailable

C=load_catalog()
HEADERS={'Origin':'http://testserver','X-VERA-Client':'browser-v2','Content-Type':'application/json'}
DAY='2026-11-11'
def profile(goals=('settlement','education','banking'),**facts):
    return {'facts':{k:{'value':v,'state':v if v in ('unknown','declined') else 'confirmed','version':1,'confirmed_at':None} for k,v in facts.items()},'goals':list(goals),'priority':goals[0] if goals else None}

def plan(p=None):return build_plan(C,p or profile(province='BC',institution='sfu'),as_of=DAY)
def portable():return {'schema_version':2,'goal':'Fictional test','profile':profile(province='BC',institution='sfu'),'plan':plan()}

def test_multi_topic_and_campus_scope():
    p=profile(province='BC',institution='ubc_okanagan')
    ids={p['id'] for p in available_programs(C,p)}
    assert {'bc_nsp','studentaid_bc','banking_basics','institution_handoff'}<=ids
    assert 'ubc_support' not in ids and 'sfu_support' not in ids

def test_banking_never_requires_student_or_immigration_facts():
    result=plan(profile(('banking',)))
    assert result['tasks'] and all(t['dependencies']==[] for t in result['tasks'])

def test_correction_preserves_unrelated_completed_edits_and_notes():
    p=profile(province='BC',institution='sfu',institution_service='unknown')
    before=plan(p);before['notes']='Keep my question'
    bank=next(t for t in before['tasks'] if t['topic']=='banking');bank.update(completion='done',user_text='My bank visit')
    nsp=next(t for t in before['tasks'] if t['id']=='bc_nsp.contact');nsp.update(completion='done',user_text='My school question')
    p['facts']['institution_service']['value']='no';p['facts']['institution_service']['state']='confirmed'
    after=build_plan(C,p,previous=before,as_of=DAY)
    b=next(t for t in after['tasks'] if t['id']==bank['id']);n=next(t for t in after['tasks'] if t['id']==nsp['id'])
    assert b['completion']=='done' and b['user_text']=='My bank visit'
    assert n['completion']=='todo' and n['user_text']=='My school question' and n['review_reason']=='facts_changed'
    assert 'does not offer' in n['text'] and after['notes']==before['notes']

def test_locale_keeps_ids_facts_and_completion():
    p=profile(province='BC',institution='sfu');en=plan(p);en['tasks'][0]['completion']='done'
    fr=build_plan(C,p,'fr',en,as_of=DAY)
    assert [t['id'] for t in en['tasks']]==[t['id'] for t in fr['tasks']]
    assert fr['tasks'][0]['completion']=='done' and fr['tasks'][0]['text']!=en['tasks'][0]['text']
    assert 'Je ne sais pas' in fr['enquiries'][0]['text']

def test_completed_removed_route_is_kept_for_review():
    p=profile(institution='sfu');before=plan(p)
    next(t for t in before['tasks'] if t['program_id']=='sfu_support')['completion']='done'
    p['facts']['institution']['value']='other'
    after=build_plan(C,p,previous=before,as_of=DAY)
    assert any(t['program_id']=='sfu_support' and t['review_reason']=='route_removed' for t in after['tasks'])

def test_sources_expire_on_bc_calendar_day():
    p=profile(('banking',));old=plan(p)
    later=build_plan(C,p,previous=old,as_of='2026-12-12')
    assert all(t['readiness']=='stale' for t in later['tasks'])
    assert not search_knowledge(C,'bank account',['banking'],as_of='2026-12-12')

def test_source_version_change_revalidates_import():
    raw=portable();raw['plan']['tasks'][0]['source_versions']['D19']='old'
    valid=validate_import(raw,C);after=build_plan(C,valid['profile'],previous=valid['plan'],as_of=DAY)
    assert after['tasks'][0]['review_reason']=='source_changed'

@pytest.mark.parametrize('mutate',[
    lambda r:r.update(consent=True),
    lambda r:r['plan']['tasks'][0].update(destination='https://evil.example'),
    lambda r:r['plan']['tasks'][0].update(program_id='invented'),
    lambda r:r['profile']['facts'].update(passport={'value':'secret','state':'confirmed','version':1,'confirmed_at':None}),
    lambda r:r['plan']['tasks'].append(copy.deepcopy(r['plan']['tasks'][0])),
    lambda r:r['plan']['tasks'][0].update(due_date='2026-11-30'),
])
def test_import_rejects_tampered_contract(mutate):
    raw=portable();mutate(raw)
    with pytest.raises(ValueError):validate_import(raw,C)

def test_child_benefits_have_one_application_route():
    p=profile(('benefits',),province='BC',children='yes');result=plan(p)
    assert len([t for t in result['tasks'] if t['id']=='family_support.apply'])==1
    assert not any('bc_family.apply' in t['id'] for t in result['tasks'])
    p['facts']['children']['value']='no'
    assert not any(t['program_id']=='family_support' for t in plan(p)['tasks'])

@pytest.mark.parametrize('query,topic,expected',[
    ('ouvrir un compte bancaire et les frais','banking','D09'),
    ('bourses et paiement des frais de scolarité SFU','education','D06'),
    ('résidence fiscale nouvel arrivant','taxes','D11'),
    ('demande allocation enfants','benefits','D13'),
    ('settlement services in my city','settlement','D02'),
])
def test_bilingual_retrieval(query,topic,expected):
    assert expected in {c['source_id'] for c in search_knowledge(C,query,[topic],'fr',limit=5,as_of=DAY)}

def test_grounding_requires_retrieved_citations():
    raw={'topics':['banking'],'proposed_facts':[],'blocks':[{'text':'Compare account fees.','citations':['D09.overview']}],'questions':[],'program_ids':['banking_basics']}
    with pytest.raises(ValueError):validate_turn(raw,[],C)
    evidence=search_knowledge(C,'bank account',['banking'],as_of=DAY)
    assert validate_turn(raw,evidence,C)
    raw['blocks'][0]['text']='You are eligible for a free account.'
    with pytest.raises(ValueError):validate_turn(raw,evidence,C)

@pytest.fixture
def client():
    with TestClient(create_app(Settings(origin='http://testserver'))) as c:
        c.headers.update(HEADERS);yield c

def session_profile(client,p=None):
    assert client.post('/api/v1/sessions',json={'consent':False,'locale':'en'}).status_code==200
    r=client.patch('/api/v1/sessions/current/profile',json={'profile_version':0,'plan_version':0,'profile':p or profile(province='BC'),'locale':'en'})
    assert r.status_code==200,r.text
    return r.json()

def test_api_capabilities_no_secret_or_fake_live_mode(client):
    r=client.get('/api/v1/capabilities').json()
    assert r['online_available'] is False and r['screening_enabled'] is False
    assert 'api_key' not in str(r)
    assert client.post('/api/v1/sessions',json={'consent':True,'locale':'en'}).status_code==503

def test_api_origin_and_unknown_fields_rejected(client):
    assert client.post('/api/v1/sessions',json={'consent':False},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/v1/sessions',json={'consent':False,'key':'secret'}).status_code==422
    assert client.post('/api/v1/sessions',content='x'*100001).status_code==413

def test_api_sessions_isolated_and_cookie_flags(client):
    r=client.post('/api/v1/sessions',json={'consent':False,'locale':'en'})
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
    other=TestClient(client.app);other.headers.update(HEADERS)
    assert other.get('/api/v1/sessions/current/plan').status_code==401

def test_api_conflict_and_delete(client):
    r=session_profile(client)
    stale={'profile_version':0,'plan_version':0,'profile':profile(('banking',)),'locale':'en'}
    assert client.patch('/api/v1/sessions/current/profile',json=stale).status_code==409
    assert client.request('DELETE','/api/v1/sessions/current',json={}).status_code==200
    assert client.get('/api/v1/sessions/current/plan').status_code==401

def test_api_expiry(client):
    session_profile(client)
    for s in client.app.state.sessions.items.values():s.touched-=4000
    assert client.get('/api/v1/sessions/current/plan').status_code==401

def test_api_import_does_not_authorize_provider(client):
    r=session_profile(client)
    response=client.post('/api/v1/sessions/current/import',json={'profile_version':r['profile_version'],'plan_version':r['plan_version'],'portable':portable()})
    assert response.status_code==200,response.text
    assert response.json()['requires_new_consent'] is True
    assert all(s.consent is False for s in client.app.state.sessions.items.values())

def test_api_failure_retries_are_idempotent(client):
    session_profile(client);current=client.get('/api/v1/sessions/current/plan').json()
    body={'profile_version':current['profile_version'],'plan_version':current['plan_version'],'message':'Compare bank fees','locale':'en','idempotency_key':'retry_test_001'}
    a=client.post('/api/v1/sessions/current/messages',json=body).json()
    b=client.post('/api/v1/sessions/current/messages',json=body).json()
    assert a==b and a['error']['code']=='ai_unavailable'
    body['message']='different'
    assert client.post('/api/v1/sessions/current/messages',json=body).status_code==409

def test_explicit_online_consent_can_preserve_an_offline_plan():
    raw=portable();raw['plan']['tasks'][-1]['completion']='done';raw['plan']['notes']='Keep this note'
    with TestClient(create_app(Settings(api_key='fake',model='test-model',origin='http://testserver'))) as c:
        c.headers.update(HEADERS)
        r=c.post('/api/v1/sessions',json={'consent':True,'locale':'en','portable':raw})
        assert r.status_code==200
        assert r.json()['plan']['notes']=='Keep this note'
        assert r.json()['plan']['tasks'][-1]['completion']=='done'
        assert next(iter(c.app.state.sessions.items.values())).consent is True

def test_model_tool_flow_and_support_gate_are_actual_mock_calls():
    calls=[]
    async def fake(settings,messages,tools,system=None):
        calls.append(tools[0]['name'])
        if tools[0]['name']=='support_review':return {'content':[{'type':'tool_use','name':'support_review','input':{'supported':True}}]}
        if len(calls)==1:return {'content':[{'type':'tool_use','id':'one','name':'search_knowledge','input':{'query':'Compare bank account fees','topics':['banking']}}]}
        return {'content':[{'type':'tool_use','id':'two','name':'prepare_turn','input':{'topics':['banking'],'proposed_facts':[],'blocks':[{'text':'Compare fees and confirm accepted identification with the institution.','citations':['D09.overview']}],'questions':[],'program_ids':['banking_basics']}}]}
    s=Session(True,'en');s.profile=profile(('banking',))
    result=asyncio.run(converse(Settings(api_key='fake',model='test-model'),s,Message(message='Bank accounts',locale='en',profile_version=0,plan_version=0,idempotency_key='test_0001'),C,Budget(),fake))
    assert len(calls)==3 and result['events'][-1]['tool']=='support_review' and result['model']=='test-model'

def test_model_repeated_tools_stop_without_claims():
    async def repeat(settings,messages,tools,system=None):return {'content':[{'type':'tool_use','id':'same','name':'search_knowledge','input':{'query':'bank','topics':['banking']}}]}
    with pytest.raises(ProviderUnavailable):
        asyncio.run(converse(Settings(api_key='fake',model='test-model'),Session(True,'en'),Message(message='bank',locale='en',profile_version=0,plan_version=0,idempotency_key='test_0002'),C,Budget(),repeat))
