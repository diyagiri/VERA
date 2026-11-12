"""Optional same-origin FastAPI runtime. Run a single worker; see docs/API.md."""
import asyncio, json, hashlib, secrets, time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, deque
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from api_contracts import SessionCreate, Message, ProfilePatch, TaskPatch, PlanPatch, ImportRequest
from settings import Settings
from sessions import Sessions
from catalog import load_catalog, bc_today
from planning import build_plan, validate_import
from conversation import converse, provider_request, Budget, ProviderUnavailable

def create_app(settings=None, provider_call=None):
    settings=settings or Settings.from_env()
    catalog=load_catalog(); sessions=Sessions(settings); budget=Budget()
    app=FastAPI(title='VERA preparation API',version='2',docs_url='/api/docs',redoc_url=None)
    app.state.sessions=sessions; app.state.budget=budget
    rate={}; salt=secrets.token_bytes(32)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic errors can contain input values: do not echo personal data.
        return JSONResponse({'error':{'code':'invalid_request','retryable':False}},status_code=422)

    @app.middleware('http')
    async def protect(request, call_next):
        path=request.url.path
        if path.startswith('/api/') and request.method not in ('GET','HEAD','OPTIONS'):
            if request.headers.get('origin') != settings.origin or request.headers.get('x-vera-client') != 'browser-v2':
                return JSONResponse({'error':{'code':'origin_rejected','retryable':False}},status_code=403)
            if request.headers.get('content-type','').split(';')[0] != 'application/json':
                return JSONResponse({'error':{'code':'json_required','retryable':False}},status_code=415)
            body=await request.body()
            if len(body)>100000:
                return JSONResponse({'error':{'code':'request_too_large','retryable':False}},status_code=413)
            # Short-lived keyed IP buckets; no raw addresses or request contents retained.
            now=time.monotonic()
            for k in list(rate):
                if not rate[k] or now-rate[k][-1]>60: del rate[k]
            key=hashlib.sha256(salt+(request.client.host if request.client else 'unknown').encode()).hexdigest()
            bucket=rate.setdefault(key,deque())
            while bucket and now-bucket[0]>60: bucket.popleft()
            if len(bucket)>=60:
                return JSONResponse({'error':{'code':'rate_limit','retryable':True}},status_code=429)
            bucket.append(now)
        result=await call_next(request)
        result.headers['X-Content-Type-Options']='nosniff'
        result.headers['Referrer-Policy']='no-referrer'
        if path.startswith('/api/') or path=='/health': result.headers['Cache-Control']='no-store'
        return result

    def get_session(request):
        session=sessions.get(request.cookies.get('vera_session'))
        if not session: raise HTTPException(401,detail={'code':'session_expired','retryable':False})
        return session

    def versions(session):
        return {'schema_version':2,'profile_version':session.profile_version,
                'plan_version':session.plan['plan_version'] if session.plan else 0}

    def check_version(session, body):
        if body.profile_version!=session.profile_version or body.plan_version!=(session.plan['plan_version'] if session.plan else 0):
            raise HTTPException(409,detail={'code':'stale_version','current':versions(session),'retryable':False})

    def envelope(session):
        return dict(versions(session),profile=session.profile,plan=session.plan,goal=session.goal,locale=session.locale)

    def refresh(session):
        if session.plan and session.plan['as_of']!=bc_today():
            session.plan=build_plan(catalog,session.profile,session.locale,session.plan,session.profile_version)

    @app.get('/health')
    async def health(): return {'status':'ok','schema_version':2,'online_available':settings.online}

    @app.get('/runtime.json')
    async def runtime(): return {'api_available':True}

    @app.get('/api/v1/capabilities')
    async def capabilities():
        return dict(schema_version=2,online_available=settings.online,provider='Anthropic' if settings.online else None,
                    model=settings.model if settings.online else None,locales=catalog['locales'],coverage=catalog['coverage'],
                    session_ttl_seconds=settings.ttl_seconds,screening_enabled=False)

    @app.post('/api/v1/sessions')
    async def create(body: SessionCreate, request: Request, response: Response):
        if body.consent and not settings.online: raise HTTPException(503,detail={'code':'ai_unavailable','retryable':False})
        try:portable=validate_import(body.portable.model_dump(),catalog) if body.portable else None
        except ValueError:raise HTTPException(422,detail={'code':'invalid_import','retryable':False})
        sessions.delete(request.cookies.get('vera_session'))
        try:sid,session=sessions.create(body.consent,body.locale)
        except ValueError:raise HTTPException(503,detail={'code':'capacity','retryable':True})
        if portable:
            session.profile=portable['profile'];session.profile_version=portable['plan']['profile_version']+1;session.goal=portable['goal']
            session.plan=build_plan(catalog,session.profile,body.locale,portable['plan'],session.profile_version)
        response.set_cookie('vera_session',sid,httponly=True,secure=settings.secure_cookie,samesite='strict',path='/api/v1',max_age=settings.ttl_seconds)
        return envelope(session)

    @app.get('/api/v1/sessions/current/plan')
    async def get_plan(request: Request):
        session=get_session(request)
        async with session.lock:
            refresh(session)
            return envelope(session)

    @app.post('/api/v1/sessions/current/messages')
    async def message(body: Message, request: Request):
        session=get_session(request)
        async with session.lock:
            digest=hashlib.sha256(body.model_dump_json().encode()).hexdigest()
            cached=session.retries.get(body.idempotency_key)
            if cached:
                if cached[0]!=digest: raise HTTPException(409,detail={'code':'idempotency_conflict','retryable':False})
                return cached[1]
            refresh(session);check_version(session,body)
            try:
                turn=await converse(settings,session,body,catalog,budget,provider_call or provider_request)
            except (Exception, asyncio.TimeoutError) as exc:
                code=str(exc) if isinstance(exc,ProviderUnavailable) else 'provider_unavailable'
                allowed={'ai_unavailable','remove_identifiers','budget_exhausted','unsupported_claim','invalid_response','invalid_tool','tool_limit','invalid_route','request_limit'}
                if code not in allowed:code='provider_unavailable'
                result=dict(envelope(session),error={'code':code,'retryable':code=='provider_unavailable'},mode='offline_available')
                session.retries[body.idempotency_key]=(digest,result)
                return result
            session.goal=body.message;session.locale=body.locale
            session.recent=(session.recent+[body.message])[-2:]
            result=dict(envelope(session),turn=turn)
            session.retries[body.idempotency_key]=(digest,result)
            if len(session.retries)>40:del session.retries[next(iter(session.retries))]
            return result

    @app.patch('/api/v1/sessions/current/profile')
    async def profile(body: ProfilePatch, request: Request):
        session=get_session(request)
        async with session.lock:
            refresh(session);check_version(session,body)
            new=body.profile.model_dump()
            changed=new['goals']!=session.profile['goals'] or new['priority']!=session.profile['priority']
            for key,fact in new['facts'].items():
                old=session.profile['facts'].get(key,{})
                different=(old.get('value'),old.get('state'))!=(fact['value'],fact['state'])
                changed=changed or different
                fact['version']=old.get('version',0)+(1 if different else 0)
                fact['confirmed_at']=datetime.now(timezone.utc).isoformat() if different and fact['state']=='confirmed' else old.get('confirmed_at')
            changed=changed or set(new['facts'])!=set(session.profile['facts'])
            if changed:session.profile_version+=1
            session.profile=new;session.locale=body.locale
            session.plan=build_plan(catalog,new,body.locale,session.plan,session.profile_version)
            return envelope(session)

    @app.patch('/api/v1/sessions/current/tasks/{task_id}')
    async def task(task_id: str, body: TaskPatch, request: Request):
        session=get_session(request)
        async with session.lock:
            refresh(session);check_version(session,body)
            target=next((t for t in (session.plan or {}).get('tasks',[]) if t['id']==task_id),None)
            if not target:raise HTTPException(404,detail={'code':'unknown_task','retryable':False})
            if body.accept_revision:
                if target['review_reason'] in ('source_stale','route_removed'):raise HTTPException(409,detail={'code':'official_review_needed','retryable':False})
                target.update(readiness='needs_official_confirmation',review_reason=None,completion='todo')
            if body.completion=='done' and target['readiness']=='stale':raise HTTPException(409,detail={'code':'review_required','retryable':False})
            if body.completion is not None:target['completion']=body.completion
            if 'user_text' in body.model_fields_set:target['user_text']=body.user_text
            session.plan['plan_version']+=1
            return envelope(session)

    @app.patch('/api/v1/sessions/current/plan')
    async def edit_plan(body: PlanPatch, request: Request):
        session=get_session(request)
        async with session.lock:
            refresh(session);check_version(session,body)
            if not session.plan:raise HTTPException(404)
            if body.notes is not None:session.plan['notes']=body.notes
            if body.enquiry_id is not None:
                e=next((e for e in session.plan['enquiries'] if e['program_id']==body.enquiry_id),None)
                if e is None or body.enquiry_text is None:raise HTTPException(422)
                e['user_text']=body.enquiry_text;e['needs_review']=False
            session.plan['plan_version']+=1
            return envelope(session)

    @app.post('/api/v1/sessions/current/import')
    async def import_plan(body: ImportRequest, request: Request):
        session=get_session(request)
        async with session.lock:
            check_version(session,body)
            try:portable=validate_import(body.portable.model_dump(),catalog)
            except ValueError:raise HTTPException(422,detail={'code':'invalid_import','retryable':False})
            session.profile=portable['profile'];session.profile_version+=1;session.goal=portable['goal']
            session.locale=portable['plan']['locale']
            session.plan=build_plan(catalog,session.profile,session.locale,portable['plan'],session.profile_version)
            # Import never authorizes AI. A new explicit consent session is required.
            session.consent=False;session.recent=[];session.retries={}
            return dict(envelope(session),requires_new_consent=True)

    @app.get('/api/v1/sources/{source_id}')
    async def source(source_id: str):
        source_id=catalog['aliases'].get(source_id,source_id)
        record=next((s for s in catalog['sources'] if s['id']==source_id),None)
        if not record:raise HTTPException(404)
        return {'schema_version':2,'source':record}

    @app.delete('/api/v1/sessions/current')
    async def delete(request: Request, response: Response):
        sessions.delete(request.cookies.get('vera_session'))
        response.delete_cookie('vera_session',path='/api/v1')
        return {'deleted':True,'schema_version':2}

    dist=Path(__file__).resolve().parent/'dist'
    if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='web')
    return app

app=create_app()
