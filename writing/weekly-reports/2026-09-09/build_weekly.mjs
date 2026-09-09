// 从同目录 Markdown 重建 HTML。依赖 marked 与 playwright；CHROME_PATH 可指定浏览器。
// node build_weekly.mjs；SKIP_RENDER=1 可仅生成保留 LaTeX 的 HTML。
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {marked}=await import(require.resolve('marked'));
const dir=path.dirname(fileURLToPath(import.meta.url));
const stem='latent_memory_12slides_2026-09-09';
const source=await fs.readFile(path.join(dir,stem+'.md'),'utf8');
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function md(text){
 const math=[];
 text=text.replace(/\$\$([\s\S]*?)\$\$|(?<!\$)\$([^\n$]+)\$(?!\$)/g,(_,block,inline)=>{
  const i=math.length;math.push(block!==undefined?`<div class="formula">\\[${esc(block.trim())}\\]</div>`:`<span class="inline-math">\\(${esc(inline)}\\)</span>`);return `LATEXPLACEHOLDER${i}END`;
 });
 let out=marked.parse(text);
 math.forEach((m,i)=>{const key=`LATEXPLACEHOLDER${i}END`;out=out.replace(`<p>${key}</p>`,m).replace(key,m)});
 return out;
}
const pieces=[...source.matchAll(/^## 第 (\d+) 页｜([^\n]+)\n([\s\S]*?)(?=^## 第 |$(?![\s\S]))/gm)];
if(pieces.length!==12)throw Error(`Expected 12 pages, got ${pieces.length}`);
const pages=pieces.map(([,n,title,body])=>{
 const parts=[...body.matchAll(/^### ([^\n]+)\n([\s\S]*?)(?=^### |$(?![\s\S]))/gm)];
 const content=parts.filter(p=>['上屏文字','表格'].includes(p[1])).map(p=>md(p[2])).join('');
 const fig=parts.filter(p=>p[1]==='配图').map(p=>md(p[2])).join('');
 const notes=parts.filter(p=>p[1].startsWith('备注')).map(p=>md(p[2])).join('');
 const isCover=n==='01',isEnd=n==='12';
 return {n,title,html:`<section class="sheet" id="page-${n}"><article class="page ${isCover?'cover':isEnd?'ending':''}"><header class="page-heading"><div class="eyebrow">视觉记忆研究 · WEEKLY REPORT</div><h2>${esc(title)}</h2></header><div class="slide-body ${fig?'with-figure':''}"><div class="copy-content">${content}</div>${fig?`<figure>${fig}</figure>`:''}</div><footer><span>2026.09.09 · ${isCover?'文献调研':isEnd?'讨论':`正文 ${String(Number(n)-1).padStart(2,'0')} / 10`}</span><span>${n} / 12</span></footer></article><div class="below"><button class="copy" data-page="page-${n}">复制上屏文字</button><details><summary>备注与来源</summary>${notes}</details></div></section>`};
});
const css=`:root{color-scheme:light;--ink:#13253c;--blue:#143c6a;--link:#2d628e}*{box-sizing:border-box}body{margin:0;background:#f3f5f7;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.6}a{color:var(--link)}nav{max-width:1120px;margin:24px auto;padding:20px 32px;background:#fff;border:1px solid #dde4ec;border-radius:8px}nav h1{font-size:24px;margin:0 0 8px}nav p{margin:6px 0;color:#52647a;font-size:15px}.toc{display:grid;grid-template-columns:repeat(3,1fr);gap:5px 20px;font-size:14px;margin-top:12px}.toc a{text-decoration:none}button{padding:6px 12px;border:1px solid #bdc9d7;border-radius:4px;background:white;color:var(--blue);font:inherit;font-size:14px;cursor:pointer}.sheet{max-width:1120px;margin:24px auto}.page{width:1120px;height:700px;background:white;border:1px solid #dfe6ed;border-radius:6px;padding:26px 40px 22px;display:flex;flex-direction:column;box-shadow:0 4px 18px #102d4510}.eyebrow{font-size:12px;letter-spacing:1.5px;color:#6b7c90}h2{font-size:30px;line-height:1.3;font-weight:650;margin:8px 0 22px;color:var(--ink)}.slide-body{flex:1;min-height:0;font-size:20px;line-height:1.65}.slide-body p{margin:0 0 12px}.slide-body p:has(>strong:only-child){margin:12px 0 3px;color:var(--blue);font-size:20px}.slide-body p:first-child{margin-top:0}.with-figure{display:grid;grid-template-columns:42% 55%;column-gap:3%;align-items:center}.with-figure .copy-content{font-size:18px;line-height:1.65}.with-figure .copy-content p{margin-bottom:13px}.with-figure .copy-content p:has(>strong:only-child){margin-bottom:3px}.with-figure figure{margin:0;min-width:0}.with-figure figure p{font-size:12px;color:#5a6b80;line-height:1.5;margin:12px 0 0}.with-figure figure img{display:block;width:100%;height:auto;max-height:435px;object-fit:contain;cursor:zoom-in}.with-figure figure p:first-child{margin:0}.formula{font-size:21px;text-align:center;margin:12px 0;line-height:1.5}.formula mjx-container{margin:0!important}.inline-math mjx-container{font-size:100%!important}table{border-collapse:collapse;width:100%;font-size:18px;margin:14px 0 18px}th{background:#edf2f7;color:var(--blue);font-weight:600}td,th{border:1px solid #cdd7e2;padding:10px 12px;text-align:left;vertical-align:top}footer{display:flex;justify-content:space-between;border-top:1px solid #dfe6ed;margin-top:14px;padding-top:10px;color:#6b7c90;font-size:12px}.cover h2{font-size:42px;max-width:880px;margin-top:28px}.cover .slide-body{display:flex;align-items:center}.cover .copy-content{font-size:23px}.cover .copy-content p{margin:18px 0}.cover .copy-content p:has(>strong:only-child){font-size:28px}.ending .slide-body{display:flex;align-items:center}.below{padding:12px 5px;display:flex;align-items:flex-start;gap:16px}.below details{flex:1;font-size:15px}.below summary{cursor:pointer;color:#62748b}.below details p{margin:10px 0}.below .copy{white-space:nowrap}.render-note{font-size:12px;color:#6b7c90}@media(max-width:1140px){nav,.sheet{margin:16px 12px}.page{width:100%;height:auto;min-height:700px}.with-figure{grid-template-columns:44% 53%}.toc{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.page{padding:24px}.with-figure{display:block}.with-figure figure{margin-top:20px}h2{font-size:26px}.slide-body{font-size:18px}.cover h2{font-size:34px}.toc{display:block}.toc a{display:block}.below{display:block}.below button{margin-bottom:10px}}@page{size:1120px 700px;margin:0}@media print{body{background:white}nav,.below{display:none}.sheet{margin:0;max-width:none;break-after:page}.sheet:last-child{break-after:auto}.page{width:1120px;height:700px;min-height:0;border:0;border-radius:0;box-shadow:none;padding:26px 40px 22px;overflow:hidden}.with-figure{display:grid;grid-template-columns:42% 55%}.with-figure figure{margin:0}a{color:inherit;text-decoration:none}}`;
let output=`<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>潜记忆研究进展 · 2026-09-09 周报</title><style>${css}</style><script id="math-config">window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']],displayMath:[['\\\\[','\\\\]']]},svg:{fontCache:'local'},startup:{typeset:true}};</script><script id="math-loader" defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script></head><body><nav><h1>潜记忆研究进展 · 周报阅读版</h1><p>20 篇新作＋20 篇视频流工作｜封面＋10 页正文＋结束页</p><p><a href="${stem}.md">Markdown 内容稿</a> · <a href="../../../research/literature/latent_memory_followup_2026-09-09.md">40 篇联合调研报告</a> · <button onclick="window.print()">打印 / 保存 PDF</button></p><div class="toc">${pages.map(p=>`<a href="#page-${p.n}">${p.n} · ${esc(p.title)}</a>`).join('')}</div></nav>${pages.map(p=>p.html).join('\n')}<script id="ui-actions">document.querySelectorAll('.copy').forEach(b=>b.onclick=async()=>{const el=document.querySelector('#'+b.dataset.page+' .copy-content');try{await navigator.clipboard.writeText(el.innerText);b.textContent='已复制';setTimeout(()=>b.textContent='复制上屏文字',1400)}catch{b.textContent='请选中文字复制'}});document.querySelectorAll('figure img').forEach(im=>im.onclick=()=>window.open(im.src,'_blank'));</script></body></html>`;
const outfile=path.join(dir,stem+'.html');await fs.writeFile(outfile,output);
if(!process.env.SKIP_RENDER){
 const {chromium}=require('playwright');
 const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900},deviceScaleFactor:1});
  await page.goto('file://'+outfile,{waitUntil:'networkidle',timeout:60000});
  await page.waitForFunction(()=>window.MathJax?.startup?.promise,{timeout:45000});
  await page.evaluate(()=>window.MathJax.startup.promise);
  if(await page.locator('mjx-merror').count())throw Error('MathJax error');
  const metrics=await page.locator('.page').evaluateAll(els=>els.map(el=>({title:el.querySelector('h2').textContent,bodyHeight:el.querySelector('.slide-body').clientHeight,bodyScroll:el.querySelector('.slide-body').scrollHeight,height:el.clientHeight,scroll:el.scrollHeight})));
  if(metrics.some(x=>x.scroll>x.height+1||x.bodyScroll>x.bodyHeight+1))throw Error('Page overflow '+JSON.stringify(metrics));
  if(await page.locator('.formula mjx-container').count()!==3)throw Error('Expected three display formulas');
  await page.evaluate(()=>{document.querySelectorAll('#math-config,#math-loader').forEach(s=>s.remove());document.querySelectorAll('[id^="MathJax"]').forEach(s=>s.remove())});
  output='<!DOCTYPE html>\n'+await page.locator('html').evaluate(el=>el.outerHTML);await fs.writeFile(outfile,output);
  console.log(JSON.stringify({pages:pages.length,body_pages:10,math:await page.locator('mjx-container').count(),metrics},null,2));
 }finally{await browser.close()}
}else console.log('Wrote 12 pages; browser rendering skipped.');
