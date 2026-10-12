import { chromium } from '/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright/index.mjs';
import fs from 'fs';
const b=await chromium.launch({executablePath:'/usr/bin/google-chrome'});const p=await b.newPage();
const d=f=>'data:image/svg+xml;base64,'+fs.readFileSync(f).toString('base64');
const o=[['A-check-t.svg','A · Check T'],['B-field.svg','B · Answer box'],['C-level.svg','C · Level T']];
await p.setViewportSize({width:760,height:470});
await p.setContent(`<body style="margin:0;background:#fff;font:600 20px Inter,Helvetica,sans-serif;color:#191B1C;display:flex;gap:40px;padding:40px">${o.map(([f,l])=>`<div><div style="margin-bottom:20px">${l}</div><img src="${d(f)}" width=200><div style="display:flex;gap:18px;align-items:end;margin:24px 0">${[48,32,16].map(s=>`<img src="${d(f)}" width=${s}>`).join('')}</div><div style="display:flex;align-items:center;gap:14px"><img src="${d(f)}" width=56><span style="font:700 40px Inter,Helvetica,sans-serif;color:#1F3A8A;letter-spacing:-1px">tapat</span></div></div>`).join('')}</body>`);
await p.screenshot({path:'compare.png'});await b.close();
