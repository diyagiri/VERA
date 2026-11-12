export class ApiClient{
 constructor(){this.profileVersion=0;this.planVersion=0;this.active=false;this.pending=null;this.controller=null;}
 async request(path,method='GET',body,signal){const response=await fetch('/api/v1'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-VERA-Client':'browser-v2'},signal,...(body!==undefined?{body:JSON.stringify(body)}:{})});
  let result;try{result=await response.json();}catch{throw Error('api_unavailable');}
  if(!response.ok){const code=result.detail?.code||result.error?.code||'api_unavailable';const e=Error(code);e.current=result.detail?.current||result.current;throw e;}
  if(result.profile_version!==undefined){this.profileVersion=result.profile_version;this.planVersion=result.plan_version;}return result;}
 async capabilities(){try{const runtime=await fetch('./runtime.json').then(r=>r.json());return runtime.api_available?await this.request('/capabilities'):{online_available:false};}catch{return {online_available:false};}}
 versions(){return {profile_version:this.profileVersion,plan_version:this.planVersion};}
 async start(locale,portable=null){const r=await this.request('/sessions','POST',{locale,consent:true,portable});this.active=true;return r;}
 async profile(profile,locale){return this.request('/sessions/current/profile','PATCH',{...this.versions(),profile,locale});}
 async message(message,locale){const signature=JSON.stringify({message,locale,...this.versions()});if(this.pending?.signature!==signature)this.pending={signature,body:{...this.versions(),message,locale,idempotency_key:crypto.randomUUID()}};this.controller=new AbortController();try{const r=await this.request('/sessions/current/messages','POST',this.pending.body,AbortSignal.any([this.controller.signal,AbortSignal.timeout(185000)]));this.pending=null;return r;}catch(e){if(e.name==='AbortError'||e.name==='TimeoutError')throw Error('request_cancelled');throw e;}finally{this.controller=null;}}
 cancel(){this.controller?.abort();}
 async task(id,patch){return this.request('/sessions/current/tasks/'+encodeURIComponent(id),'PATCH',{...this.versions(),...patch});}
 async plan(patch){return this.request('/sessions/current/plan','PATCH',{...this.versions(),...patch});}
 async clear(){if(this.active){try{await this.request('/sessions/current','DELETE',{});}finally{this.active=false;}}}
}
