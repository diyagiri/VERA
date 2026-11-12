import {createServer} from 'node:http';
import {webcrypto} from 'node:crypto';
import worker from '../dist/server/index.js';
import {localDatabase} from './sqlite_d1.mjs';
// No credentials are read from the repository or exposed to the browser.
const env={DB:localDatabase(),VERA_SESSION_SECRET:Buffer.from(webcrypto.getRandomValues(new Uint8Array(32))).toString('base64')};
const server=createServer(async(req,res)=>{try{const chunks=[];for await(const c of req)chunks.push(c);const host=req.headers.host;const request=new Request(`http://${host}${req.url}`,{method:req.method,headers:req.headers,...(!['GET','HEAD'].includes(req.method)?{body:Buffer.concat(chunks)}:{})});const response=await worker.fetch(request,env,{waitUntil(p){p.catch(()=>{});}});res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));}catch{res.writeHead(500);res.end('Preview unavailable');}});
const args=process.argv.slice(2);const option=name=>args.includes(name)?args[args.indexOf(name)+1]:undefined;
const port=Number(option('--port')||process.env.PORT||3000),host=option('--host')||'0.0.0.0';server.listen(port,host,()=>console.log(`VERA preview listening on ${host}:${port}`));
