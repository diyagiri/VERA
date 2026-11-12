// V2 offline preparation workflow. No model calls or browser storage in this module.
export const TOPICS=['settlement','education','banking','taxes','benefits'];
export const FACTS={province:['BC','other','unknown','declined'],city:null,student:['yes','no','unknown','declined'],institution:['sfu','ubc_vancouver','ubc_okanagan','other','unknown','declined'],institution_service:['yes','no','unknown','declined'],status:['study_permit','work_permit','permanent_resident','protected_person','citizen','other','unknown','declined'],children:['yes','no','unknown','declined'],
 // Screening facts (hybrid): categories only, never document numbers. pr_month is YYYY-MM.
 naturalized:['yes','no','unknown','declined'],special_pathway:['yes','no','unknown','declined'],pr_class:['economic','family','refugee','other','unknown','declined'],pr_month:null};
const clone=v=>JSON.parse(JSON.stringify(v));
const same=(a,b)=>JSON.stringify(Object.entries(a||{}).sort())===JSON.stringify(Object.entries(b||{}).sort());
export const bcToday=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Vancouver',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export const factValue=(profile,key)=>profile.facts[key]?.state==='confirmed'?profile.facts[key].value:'unknown';
export function sourceCurrent(s,day=bcToday()) {const age=(Date.parse(day)-Date.parse(s.checked_on))/86400000;return s.status==='available'&&age>=0&&age<=(s.freshness_days??30);}
export function detectTopics(text){
 let q=text.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'');
 q=q.replace(/(?:not (?:a |an )?student|pas (?:un |une )?etudiant(?:e)?)/g,'');
 const terms={settlement:/sett[li]|newcomer|new to|newly arrived|arriv|etabl|integration|english practice|finding work|emploi/,
 education:/stud[ye]|student|school|tuition|university|education|etude|etudiant|scolar|universit|bourse|sfu|ubc/,
 banking:/bank|account|atm|debit|fee|banqu|compte|guichet|frais banc/,
 taxes:/\btax|impot|fisc|revenue|cra|\barc\b/,
 benefits:/benefit|child|parent|famil|household|prestation|enfant|allocation/};
 return TOPICS.filter(t=>terms[t].test(q));
}
export function proposeFacts(text){
 const q=text.toLowerCase();const result={};
 if(/\bbc\b|british columbia|colombie-britannique|c\.-b\./i.test(text))result.province='BC';
 const city=['Vancouver','Victoria','Burnaby','Surrey','Kelowna','Richmond','Nanaimo','Prince George'].find(c=>q.includes(c.toLowerCase()));if(city)result.city=city;
 if(/\bsfu\b/.test(q))result.institution='sfu';
 if(/ubc.*vancouver|vancouver.*ubc/.test(q))result.institution='ubc_vancouver';
 if(/ubc.*okanagan|okanagan.*ubc/.test(q))result.institution='ubc_okanagan';
 if(/not (?:a )?student|pas (?:un |une )?étudiant/.test(q))result.student='no';
 else if(/i (?:am|study)|i’m a student|i'm a student|je suis étudiant|j’étudie/.test(q)&&/student|study|étudi/.test(q))result.student='yes';
 if(/study permit|permis d’études|permis d'etudes/.test(q))result.status='study_permit';
 if(/work permit|permis de travail/.test(q))result.status='work_permit';
 if(/permanent resident|résident permanent/.test(q))result.status='permanent_resident';
 if(/my children|with (?:two|three|\d) children|mes enfants|avec (?:deux|trois) enfants/.test(q))result.children='yes';
 return result;
}
export function availablePrograms(catalog,profile){return catalog.programs.filter(p=>{
 const school=factValue(profile,'institution');
 return profile.goals.includes(p.topic)&&(!p.institutions||p.institutions.includes(school))&&(!p.unknown_institution||!['sfu','ubc_vancouver'].includes(school))&&(!p.requires_children||factValue(profile,'children')!=='no')&&!(factValue(profile,'province')==='other'&&p.jurisdiction==='BC');
 }).sort((a,b)=>(a.topic!==profile.priority)-(b.topic!==profile.priority)||profile.goals.indexOf(a.topic)-profile.goals.indexOf(b.topic));}
export function buildPlan(catalog,profile,locale='en',previous=null,profileVersion=0,day=bcToday()){
 previous=previous||{};const sources=Object.fromEntries(catalog.sources.map(s=>[s.id,s]));const old=Object.fromEntries((previous.tasks||[]).map(t=>[t.id,t]));const oldEnq=Object.fromEntries((previous.enquiries||[]).map(e=>[e.program_id,e]));const tasks=[],enquiries=[],versions={};
 for(const p of availablePrograms(catalog,profile)){
  const values=Object.fromEntries(p.dependencies.map(f=>[f,factValue(profile,f)]));const src=Object.fromEntries(p.sources.map(id=>[id,sources[id].version]));Object.assign(versions,src);
  const stale=p.sources.some(id=>!sourceCurrent(sources[id],day));
  for(const step of p.steps){
   const id=p.id+'.'+step.id,prior=old[id];let reason=stale?'source_stale':prior?.review_reason||null;
   if(prior&&!same(prior.source_versions,src))reason='source_changed';else if(prior&&!same(prior.dependency_values,values))reason='facts_changed';
   const text=(step.variants?.values[values[step.variants.field]]||step.text)[locale];
   const t={id,program_id:p.id,topic:p.topic,group:step.group,text,destination:step.url||p.url,evidence:step.sources||p.sources,dependencies:p.dependencies,dependency_values:values,source_versions:src,
    readiness:reason?'stale':(step.requires||[]).some(f=>values[f]==='unknown')?'needs_information':step.readiness||'needs_official_confirmation',completion:prior?.completion||'todo',user_text:prior?.user_text??null,review_reason:reason,due_date:null};
   if(reason&&t.completion==='done')t.completion='todo';tasks.push(t);
  }
  const prior=oldEnq[p.id],context=Object.entries(values).map(([f,v])=>`${catalog.profile_labels[locale][f]}: ${catalog.profile_values[locale][v]||v}`).join('\n');
  enquiries.push({program_id:p.id,text:p.enquiry[locale]+(context?'\n\n'+context:''),user_text:prior?.user_text??null,dependencies:p.dependencies,dependency_values:values,source_versions:src,needs_review:stale||!!(prior&&(prior.needs_review||!same(prior.dependency_values,values)||!same(prior.source_versions,src)))});
 }
 const ids=new Set(tasks.map(t=>t.id));
 for(const prior of Object.values(old))if(!ids.has(prior.id)&&(prior.user_text||prior.completion==='done'))tasks.push({...clone(prior),readiness:'stale',review_reason:'route_removed',completion:'todo'});
 return {schema_version:2,profile_version:profileVersion,plan_version:(previous.plan_version||0)+1,as_of:day,locale,tasks,enquiries,source_versions:versions,notes:previous.notes||''};
}
function keys(o,allowed,required=allowed){if(!o||typeof o!=='object'||Array.isArray(o)||Object.keys(o).some(k=>!allowed.includes(k))||required.some(k=>!(k in o)))throw Error('invalid_import');}
function str(v,max=2000){if(typeof v!=='string'||v.length>max)throw Error('invalid_import');}
function integer(v){if(!Number.isSafeInteger(v)||v<0)throw Error('invalid_import');}
function array(v,max){if(!Array.isArray(v)||v.length>max)throw Error('invalid_import');}
export function validateProfile(p){
 keys(p,['facts','goals','priority']);keys(p.facts,Object.keys(FACTS),[]);array(p.goals,5);
 if(p.goals.some(t=>!TOPICS.includes(t))||new Set(p.goals).size!==p.goals.length||p.priority!==null&&!p.goals.includes(p.priority))throw Error('invalid_import');
 for(const [k,f]of Object.entries(p.facts)){
  keys(f,['value','state','version','confirmed_at']);str(f.value,80);integer(f.version);
  if(!['unknown','declined','proposed','confirmed'].includes(f.state)||(FACTS[k]&&!FACTS[k].includes(f.value))||(k==='city'&&/\d/.test(f.value)))throw Error('invalid_import');
  if(['unknown','declined'].includes(f.value)&&f.state!==f.value)throw Error('invalid_import');
  if(k==='pr_month'&&!['unknown','declined'].includes(f.value)&&!/^\d{4}-(0[1-9]|1[0-2])$/.test(f.value))throw Error('invalid_import');
  if(f.confirmed_at!==null)str(f.confirmed_at,80);
 }
 return p;
}
export function validatePortable(raw,catalog){
 keys(raw,['schema_version','goal','profile','plan']);if(raw.schema_version!==2)throw Error('invalid_import');str(raw.goal);validateProfile(raw.profile);
 const p=raw.plan;keys(p,['schema_version','profile_version','plan_version','as_of','locale','tasks','enquiries','source_versions','notes']);
 if(p.schema_version!==2||!['en','fr'].includes(p.locale)||!/^\d{4}-\d{2}-\d{2}$/.test(p.as_of))throw Error('invalid_import');integer(p.profile_version);integer(p.plan_version);str(p.notes,4000);array(p.tasks,100);array(p.enquiries,20);
 const programs=Object.fromEntries(catalog.programs.map(p=>[p.id,p])),sources=catalog.sources.map(s=>s.id),seen=new Set();keys(p.source_versions,sources,[]);
 for(const t of p.tasks){
  keys(t,['id','program_id','topic','group','text','destination','evidence','dependencies','dependency_values','source_versions','readiness','completion','user_text','review_reason','due_date']);
  const route=programs[t.program_id],step=route?.steps.find(s=>t.id===route.id+'.'+s.id);
  if(!step||seen.has(t.id)||t.topic!==route.topic||t.group!==step.group||t.destination!==(step.url||route.url)||t.due_date!==null)throw Error('invalid_import');seen.add(t.id);
  str(t.text,1600);if(t.user_text!==null)str(t.user_text,1600);array(t.evidence,8);array(t.dependencies,8);
  if(JSON.stringify(t.evidence)!==JSON.stringify(step.sources||route.sources)||JSON.stringify(t.dependencies)!==JSON.stringify(route.dependencies))throw Error('invalid_import');
  keys(t.dependency_values,route.dependencies);keys(t.source_versions,route.sources);for(const v of Object.values(t.dependency_values))str(v,80);for(const v of Object.values(t.source_versions))str(v,500);
  if(!['ready','needs_information','needs_official_confirmation','stale'].includes(t.readiness)||!['todo','done','dismissed'].includes(t.completion)||![null,'facts_changed','source_changed','source_stale','route_removed'].includes(t.review_reason))throw Error('invalid_import');
 }
 const enquiryIds=new Set();for(const e of p.enquiries){
  keys(e,['program_id','text','user_text','dependencies','dependency_values','source_versions','needs_review']);const route=programs[e.program_id];
  if(!route||enquiryIds.has(e.program_id)||typeof e.needs_review!=='boolean'||JSON.stringify(e.dependencies)!==JSON.stringify(route.dependencies))throw Error('invalid_import');enquiryIds.add(e.program_id);
  str(e.text,4000);if(e.user_text!==null)str(e.user_text,4000);keys(e.dependency_values,route.dependencies);keys(e.source_versions,route.sources);for(const v of Object.values(e.dependency_values))str(v,80);for(const v of Object.values(e.source_versions))str(v,500);
 }
 return clone(raw);
}
export class Workspace{
 constructor(catalog){this.catalog=catalog;this.reset();}
 reset(){this.profile={facts:{},goals:[],priority:null};this.profileVersion=0;this.plan=null;this.goal='';this.locale=this.locale||'en';}
 confirm(profile){validateProfile(profile);let changed=!same({goals:profile.goals,priority:profile.priority},{goals:this.profile.goals,priority:this.profile.priority});
  for(const[k,f]of Object.entries(profile.facts)){const old=this.profile.facts[k];const diff=!old||old.value!==f.value||old.state!==f.state;changed=changed||diff;f.version=(old?.version||0)+(diff?1:0);f.confirmed_at=diff&&f.state==='confirmed'?new Date().toISOString():old?.confirmed_at||null;}
  changed=changed||!same(Object.keys(profile.facts),Object.keys(this.profile.facts));if(changed)this.profileVersion++;
  this.profile=clone(profile);this.rebuild();}
 rebuild(day=bcToday()){this.plan=buildPlan(this.catalog,this.profile,this.locale,this.plan,this.profileVersion,day);return this.plan;}
 setLocale(locale){if(!['en','fr'].includes(locale))throw Error('invalid_locale');this.locale=locale;if(this.plan)this.rebuild();}
 import(raw){const valid=validatePortable(raw,this.catalog);this.profile=valid.profile;this.goal=valid.goal;this.locale=valid.plan.locale;this.profileVersion=Math.max(this.profileVersion,valid.plan.profile_version)+1;this.plan=buildPlan(this.catalog,this.profile,this.locale,valid.plan,this.profileVersion);}
 portable(){if(this.plan&&this.plan.as_of!==bcToday())this.rebuild();return {schema_version:2,goal:this.goal,profile:clone(this.profile),plan:clone(this.plan)};}
 updateTask(id,patch){if(this.plan.as_of!==bcToday())this.rebuild();const t=this.plan.tasks.find(t=>t.id===id);if(!t)throw Error('unknown_task');
  if(patch.accept_revision){if(['source_stale','route_removed'].includes(t.review_reason))throw Error('official_review_needed');t.review_reason=null;t.readiness='needs_official_confirmation';}
  if(patch.completion==='done'&&t.readiness==='stale')throw Error('review_required');
  if(patch.completion)t.completion=patch.completion;if('user_text'in patch)t.user_text=patch.user_text;this.plan.plan_version++;}
 markdown(strings){const p=this.plan;let lines=['# VERA',this.goal,'',`${strings.asOf}: ${p.as_of}`,strings.boundary,'',`## ${strings.profile}`];
  for(const[k,f]of Object.entries(this.profile.facts))lines.push(`- ${strings.fields[k]}: ${strings.values[f.value]||f.value}`);
  for(const group of ['prepare','act','ask']){lines.push('',`## ${strings.groups[group]}`);for(const t of p.tasks.filter(t=>t.group===group))lines.push(`- [${t.completion==='done'?'x':' '}] ${t.user_text??t.text}`,`  ${strings.states[t.readiness]}${t.review_reason?' · '+strings.reasons[t.review_reason]:''}`,`  ${t.destination}`);}
  lines.push('',`## ${strings.enquiries}`);for(const e of p.enquiries){const route=this.catalog.programs.find(p=>p.id===e.program_id);lines.push('',`### ${route.name[this.locale]}`,strings.unsent,e.user_text??e.text);}
  lines.push('',`## ${strings.notes}`,p.notes,'',`## ${strings.sources}`);for(const id of Object.keys(p.source_versions)){const s=this.catalog.sources.find(s=>s.id===id);lines.push(`- ${s.title}: ${this.locale==='fr'&&s.fr_url?s.fr_url:s.url}`);}return lines.join('\n');}
}
