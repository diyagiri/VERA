import {AppError} from './contracts.js';
import {bcToday} from '../web/navigator.js';
const tokens=s=>String(s).toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu,'').match(/[\p{L}\p{N}]+/gu)||[];
export function current(chunk,day=bcToday()){const age=(Date.parse(day)-Date.parse(chunk.checked_on))/86400000;return age>=0&&age<=(chunk.freshness_days||30)&&!['unavailable','retired','historic'].includes(chunk.status);}
export function eligibleChunks(index,topics,profile,day=bcToday()){
 const school=profile.facts?.institution?.value;
 return index.chunks.filter(c=>current(c,day)&&(!topics.length||topics.includes(c.topic))&&(!c.institution||(c.institution==='sfu'&&school==='sfu')||(c.institution==='ubc'&&school==='ubc_vancouver'))&&!(profile.facts?.province?.value==='other'&&c.jurisdiction==='BC'));
}
export function rankEvidence(chunks,query,locale,queryVector=null,vectors={}){
 const q=new Set(tokens(query));const lexical=chunks.map(c=>({c,score:tokens(c.text+' '+c.section+' '+c.source_id+' '+JSON.stringify(c.search_terms||{})).reduce((s,t)=>s+(q.has(t)?1:0),0)/Math.sqrt(20+tokens(c.text).length)})).sort((a,b)=>b.score-a.score);
 const scores=new Map();for(const [i,v]of lexical.entries())if(v.score>0)scores.set(v.c.id,1/(60+i));
 if(queryVector){const semantic=chunks.filter(c=>vectors[c.id]?.length===queryVector.length).map(c=>({c,score:queryVector.reduce((s,v,i)=>s+v*vectors[c.id][i],0)})).sort((a,b)=>b.score-a.score);for(const [i,v]of semantic.entries())scores.set(v.c.id,(scores.get(v.c.id)||0)+1/(60+i));}
 const ranked=chunks.filter(c=>scores.has(c.id)).sort((a,b)=>(scores.get(b.id)-scores.get(a.id))||((b.locale===locale)-(a.locale===locale))||a.id.localeCompare(b.id));
 const selected=[];for(const c of ranked){if(selected.length>=8)break;selected.push(c);for(const id of c.related_chunk_ids||[]){const related=chunks.find(v=>v.id===id);if(related&&selected.length<8&&!selected.some(v=>v.id===id))selected.push(related);}}
 return [...new Map(selected.map(c=>[c.id,c])).values()].slice(0,8);
}
export function checkGrounding(turn,evidence,catalog,programs){
 const ids=new Set(evidence.map(c=>c.id));const known=new Set(programs.map(p=>p.id));
 if(turn.program_ids.some(id=>!known.has(id)))throw new AppError('invalid_route');
 for(const b of turn.blocks){if(!b.citations.length||b.citations.some(id=>!ids.has(id)))throw new AppError('unsupported_claim');if(/https?:\/\/|\$\s*\d|\b\d{4}-\d{2}-\d{2}\b/.test(b.text))throw new AppError('unsupported_claim');if(/\byou (?:are|will be) eligible\b|\byou will receive\b|\bguaranteed\b|vous êtes admissible|vous recevrez|garanti/i.test(b.text))throw new AppError('unsupported_claim');}
 return turn;
}
