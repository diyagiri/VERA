// Records docs/demo/VERA_demo.mp4. Needs Playwright (npm i -D playwright) and the built site served at :8765:
//   python -m http.server 8765 --directory dist   then   node docs/demo/record_demo.js   then convert webm to mp4 with ffmpeg.
const { chromium } = require('playwright');
const W=1280,H=720;
(async()=>{
 const b=await chromium.launch();
 const ctx=await b.newContext({viewport:{width:W,height:H},recordVideo:{dir:'demo/raw',size:{width:W,height:H}}});
 const p=await ctx.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));
 const wait=ms=>p.waitForTimeout(ms);
 const cap=async(text)=>{await p.evaluate(t=>{let el=document.getElementById('demo-cap');if(!el){el=document.createElement('div');el.id='demo-cap';el.setAttribute('aria-hidden','true');
   Object.assign(el.style,{position:'fixed',left:'50%',bottom:'22px',transform:'translateX(-50%)',maxWidth:'1000px',padding:'12px 20px',background:'rgba(23,61,53,.94)',color:'#fff',font:'500 19px/1.4 Inter,Segoe UI,Arial,sans-serif',borderRadius:'12px',zIndex:99999,textAlign:'center',boxShadow:'0 6px 24px rgba(0,0,0,.25)'});document.body.appendChild(el);}
   const host=document.querySelector('dialog[open]')||document.body;if(el.parentElement!==host)host.appendChild(el);el.textContent=t;el.style.display=t?'block':'none';},text);};
 const card=async(title,sub,ms)=>{await p.evaluate(([t,s])=>{let el=document.getElementById('demo-card');if(!el){el=document.createElement('div');el.id='demo-card';Object.assign(el.style,{position:'fixed',inset:'0',background:'#173d35',color:'#fff',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',zIndex:100000,font:'600 44px/1.2 Inter,Segoe UI,Arial,sans-serif',textAlign:'center',padding:'60px'});document.body.appendChild(el);}
   el.innerHTML=`<div>${t}</div><div style="font:400 22px/1.5 Inter,Segoe UI,Arial,sans-serif;margin-top:22px;max-width:900px;opacity:.9">${s}</div>`;el.style.display='flex';},[title,sub]);await wait(ms);await p.evaluate(()=>{document.getElementById('demo-card').style.display='none';});};
 const scrollTo=async(sel,offset=90)=>{await p.evaluate(([s,o])=>{const el=document.querySelector(s);if(el)window.scrollTo({top:el.getBoundingClientRect().top+window.scrollY-o,behavior:'smooth'});},[sel,offset]);await wait(900);};
 const answer=async(v)=>{await p.check(`input[name=answer][value=${v}]`);await wait(700);await p.click('#screen-q-form button.primary');await wait(900);};

 await p.goto('http://127.0.0.1:8765/index.html',{waitUntil:'networkidle'});
 await card('VERA · Your next step in BC','Newcomer support navigator for British Columbia — hackathon demo.<br>Offline mode: no AI model is used in this recording. Mei is a fictional persona.',4500);
 await cap('Mei, a new international master’s student, describes what she needs in her own words.');
 await p.click('#goal');await p.keyboard.type("I just arrived for my master's at SFU in Burnaby. I want help settling in and to know if I can get student funding.",{delay:22});await wait(800);
 await p.click('text=Find my next steps');await wait(1200);
 await cap('VERA suggests topics and details. Nothing counts as a fact until she confirms it.');await wait(3200);
 await p.click('text=Build my plan');await wait(1200);
 await scrollTo('#screening',70);
 await cap('Program screening for three programs. Rules decide these results — not AI. One question at a time.');await wait(3800);
 await cap('VERA only asks for a category, never a document or ID number.');await wait(1500);await answer('study_permit');
 await cap('Next question, chosen because a rule needs it.');await wait(1500);await answer('yes');
 await scrollTo('#screen-demo',120);
 await cap('No rule has had independent review yet, so live results say “Needs official review”. For this demo we show the draft rule logic.');await wait(3800);
 await p.check('#screen-demo');await wait(1200);
 await scrollTo('.screen-grid',90);
 await cap('Each program is explained rule by rule. A study permit alone does not meet StudentAid BC’s status criterion.');await wait(4200);
 await p.click('.screen-card[data-program="STU-01"] .screen-evidence summary');await wait(800);
 await cap('Every result links to the official page, with when it was checked.');await wait(3500);
 await scrollTo('#screen-q-form',90);
 await cap('BC NSP serves international students only if their school doesn’t offer the service. Mei’s school doesn’t.');await wait(2800);
 await answer('no');
 await scrollTo('.screen-changes',90);
 await cap('Her answer re-runs only the affected program: BC NSP now shows no blocker in the checked criteria.');await wait(4500);
 await scrollTo('#screen-q-form',90);
 await cap('Not sure? She can skip. VERA won’t ask again, and says to check with a provider.');await wait(2600);
 await p.click('[data-screen-skip]');await wait(1200);
 await scrollTo('.screen-grid',90);await wait(2200);
 await scrollTo('.plan-summary',80);
 await cap('Her plan: practical steps across her topics, each linked to an official source.');await wait(3500);
 await scrollTo('#enquiry-text',140);
 await cap('A draft enquiry to a provider, which she can edit. Nothing is ever sent for her.');await wait(3800);
 await cap('Everything works in French too.');await p.selectOption('#language','fr');await wait(1000);await scrollTo('#screening',70);await wait(2800);
 await p.selectOption('#language','en');await wait(1000);
 await p.evaluate(()=>window.scrollTo({top:0,behavior:'smooth'}));await wait(900);
 await cap('');await p.click('[data-export]');await wait(900);
 await cap('She downloads her plan, including the screening results, as Markdown or JSON.');await wait(3500);
 await p.keyboard.press('Escape');await cap('');
 await card('VERA','Rules decide · AI assists · Official sources decide in the end.<br><br>Online mode uses Anthropic Claude once the owner adds an API key.<br>Built on Kopal Chaudhary’s thesis prototype.<br>github.com/diyagiri/VERA',5000);
 const video=p.video();await ctx.close();await b.close();
 console.log('raw', await video.path());console.log('errors',errs);
})();
