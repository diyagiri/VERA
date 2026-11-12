import {execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,readdirSync,statSync,rmSync} from 'node:fs';
import path from 'node:path';
import {build} from 'esbuild';
import {withEvidenceVersions} from '../worker/corpus.js';
// Only the allowlisted frontend output is embedded. No source archives, keys, or repository files.
execFileSync('python',['scripts/build_web.py'],{stdio:'inherit'});
const catalog=withEvidenceVersions(JSON.parse(readFileSync('data/catalog/navigation.json')),JSON.parse(readFileSync('data/evidence/index.json')));
writeFileSync('dist/navigation.json',JSON.stringify(catalog));
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
const files=['index.html','app.js','api.js','navigator.js','engine.js','styles.css','i18n.js','icon.svg','legacy.html','legacy-app.js','navigation.json','catalog.json','locales/en.json','locales/fr.json'];
const assets={};for(const file of files){const data=readFileSync(path.join('dist',file));assets['/'+file]={type:types[path.extname(file)],data:data.toString('base64')};}
writeFileSync('worker/generated-assets.js','export const ASSETS='+JSON.stringify(assets)+';\n');
mkdirSync('dist/server',{recursive:true});mkdirSync('dist/.openai',{recursive:true});
await build({entryPoints:['worker/index.js'],outfile:'dist/server/index.js',bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true,legalComments:'none'});
const manifest=JSON.parse(readFileSync('.openai/hosting.json'));delete manifest.static;manifest.d1='DB';manifest.r2=null;writeFileSync('dist/.openai/hosting.json',JSON.stringify(manifest,null,2)+'\n');
const module=await import('../dist/server/index.js?check='+Date.now());if(typeof module.default?.fetch!=='function')throw Error('Worker fetch export missing');
console.log('Built server Worker and allowlisted static assets. Runtime secret values are not build inputs.');
