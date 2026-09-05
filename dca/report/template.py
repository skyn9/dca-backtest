"""报告模板：CSS + 通用图表 JS。数据由 builder 注入 __DATA__。"""

CSS = """
:root{--ground:#FBFAF7;--panel:#FFFFFC;--ink:#16232E;--ink-2:#3B4C59;--muted:#61707C;
--rule:#E2DCD1;--rule-2:#EEE9E0;--rule-3:#F5F2EC;--gold:#C07A16;--gold-w:#F2E6CE;
--blue:#2F6FC4;--rose:#B23A5F;--pos:#1E6B48;--neg:#A6352B;
--sf:'Spectral','Songti SC','Noto Serif CJK SC',Georgia,serif;
--ss:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',system-ui,sans-serif;
--sm:'IBM Plex Mono','SF Mono',ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--ground:#121A21;--panel:#18222B;--ink:#ECE7DF;--ink-2:#C2CAD1;--muted:#8E9BA5;
--rule:#293743;--rule-2:#212C36;--rule-3:#1B242D;--gold:#C2842B;--gold-w:#33280F;
--blue:#5390DC;--rose:#D25777;--pos:#4C9B70;--neg:#D06A5E}}
:root[data-theme="dark"]{--ground:#121A21;--panel:#18222B;--ink:#ECE7DF;--ink-2:#C2CAD1;
--muted:#8E9BA5;--rule:#293743;--rule-2:#212C36;--rule-3:#1B242D;--gold:#C2842B;
--gold-w:#33280F;--blue:#5390DC;--rose:#D25777;--pos:#4C9B70;--neg:#D06A5E}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--ss);font-size:15px;line-height:1.75}
.wrap{max-width:1040px;margin:0 auto;padding:0 28px 70px}
h1,h2{font-family:var(--sf);text-wrap:balance;margin:0;line-height:1.25}
h1{font-size:clamp(28px,4vw,42px);font-weight:700;letter-spacing:-.015em}
h2{font-size:clamp(20px,2.4vw,26px);font-weight:600}
p{margin:0 0 14px}
.mono,.n{font-family:var(--sm);font-variant-numeric:tabular-nums}
.eyebrow{font-family:var(--sm);font-size:10.5px;letter-spacing:.17em;text-transform:uppercase;color:var(--muted)}
header{padding:48px 0 0}
.kicker{display:flex;gap:14px;align-items:center;margin-bottom:20px}
.kicker i{flex:1;height:1px;background:var(--rule);font-style:normal}
.lede{font-family:var(--sf);font-size:clamp(16px,1.9vw,19px);line-height:1.6;color:var(--ink-2);
max-width:62ch;margin:18px 0 0;font-weight:300}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:34px 0 0;
border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
.kpi{padding:18px 20px 20px;border-right:1px solid var(--rule-3)}
.kpi:last-child{border-right:0}
.kpi b{display:block;white-space:nowrap;font-family:var(--sm);font-size:26px;font-weight:600;
letter-spacing:-.02em;line-height:1.1}
.kpi span{display:block;font-size:11.5px;color:var(--muted);margin-top:6px;line-height:1.5}
.kpi.hi b{color:var(--gold)}
section{padding:50px 0 0}
section>hr{border:0;border-top:1px solid var(--rule);margin:0 0 38px}
.h-wrap{display:flex;align-items:baseline;gap:14px;margin-bottom:8px;flex-wrap:wrap}
.h-num{font-family:var(--sm);font-size:11.5px;color:var(--gold);letter-spacing:.1em;padding-top:4px}
.dek{color:var(--muted);font-size:13px;max-width:76ch;margin:0 0 6px}
.tw{overflow-x:auto;margin:22px 0 0}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:560px}
caption{caption-side:bottom;text-align:left;font-size:12px;color:var(--muted);padding-top:10px;line-height:1.6}
th,td{text-align:right;padding:8px 12px;border-bottom:1px solid var(--rule-3);white-space:nowrap}
th{font-family:var(--sm);font-size:10px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);
font-weight:500;border-bottom:1px solid var(--rule);vertical-align:bottom}
td:first-child,th:first-child{text-align:left;white-space:normal}
td.n{font-family:var(--sm);font-variant-numeric:tabular-nums}
td.wide{white-space:normal;font-size:12px;color:var(--muted);line-height:1.5}
tbody tr:hover{background:var(--rule-3)}
tr.sum td{border-top:1px solid var(--rule);border-bottom:0;font-weight:600;background:var(--rule-3)}
tr.hl{background:var(--gold-w)}
.pos{color:var(--pos)}.neg{color:var(--neg)}.em{color:var(--gold);font-weight:600}
.wbar{display:inline-block;height:6px;background:var(--gold);border-radius:0 2px 2px 0;vertical-align:middle}
figure{margin:24px 0 0}
figcaption{font-size:12.5px;color:var(--muted);margin-top:12px;max-width:80ch;line-height:1.65}
.chart{width:100%;height:auto;display:block;overflow:visible}
.lg{display:flex;gap:20px;flex-wrap:wrap;margin:0 0 12px;font-size:12.5px}
.lg span{display:inline-flex;align-items:center;gap:7px;color:var(--ink-2)}
.lg i{width:14px;height:3px;border-radius:2px;font-style:normal}
.note{background:var(--rule-3);border-radius:5px;padding:16px 19px;font-size:13.5px;color:var(--ink-2);margin:20px 0 0}
.note b{color:var(--ink)}
.note.warn{border-left:2px solid var(--rose)}
.heat{display:grid;gap:2px;min-width:600px}
.heat div{height:38px;display:grid;place-items:center;font-family:var(--sm);font-size:10.5px;
border-radius:2px;font-variant-numeric:tabular-nums}
.heat .lb{font-family:var(--ss);font-size:11px;color:var(--ink-2);justify-content:end;padding-right:10px;background:none}
.heat .lt{height:24px;font-family:var(--ss);font-size:10.5px;color:var(--muted);align-items:end;background:none}
footer{padding:44px 0 0;margin-top:50px;border-top:1px solid var(--rule);color:var(--muted);font-size:12.5px}
footer p{max-width:80ch}
.tip{position:fixed;pointer-events:none;background:var(--panel);border:1px solid var(--rule);border-radius:5px;
padding:9px 11px;font-size:12px;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:90;opacity:0;transition:opacity .1s;
font-family:var(--sm);font-variant-numeric:tabular-nums;line-height:1.6}
.tip b{font-family:var(--ss)}
@media (max-width:640px){.wrap{padding:0 18px 50px}.kpi{border-right:0;border-bottom:1px solid var(--rule-3)}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
"""

JS = r"""
const D=__DATA__;
const C=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const NS="http://www.w3.org/2000/svg";
const E=(n,a={})=>{const e=document.createElementNS(NS,n);for(const k in a)e.setAttribute(k,a[k]);return e;};
const T=(x,y,t,o={})=>{const e=E("text",Object.assign({x,y,"font-size":11,"font-family":"var(--sm)"},o));e.textContent=t;return e;};
const P=(v,d=2)=>v==null||v!==v?"—":(v*100).toFixed(d)+"%";
const tip=document.getElementById("tip");
const show=(x,y,h)=>{tip.innerHTML=h;tip.style.opacity=1;const r=tip.getBoundingClientRect();
 tip.style.left=Math.min(x+14,innerWidth-r.width-10)+"px";tip.style.top=Math.max(8,y-r.height-12)+"px";};
const hide=()=>tip.style.opacity=0;

function line(id,cfg){const svg=document.getElementById(id);if(!svg)return;svg.innerHTML="";
 const vb=svg.getAttribute("viewBox").split(" ").map(Number),W=vb[2],H=vb[3];
 const p=cfg.pad||{l:58,r:86,t:14,b:32},iw=W-p.l-p.r,ih=H-p.t-p.b,n=cfg.x.length;
 const X=i=>p.l+(n<2?0:i/(n-1)*iw),Y=v=>p.t+ih-(v-cfg.lo)/(cfg.hi-cfg.lo)*ih;
 cfg.ticks.forEach(t=>{const y=Y(t),z=cfg.zero!==undefined&&Math.abs(t-cfg.zero)<1e-9;
  svg.appendChild(E("line",{x1:p.l,x2:p.l+iw,y1:y,y2:y,stroke:z?C("--muted"):C("--rule-2"),
   "stroke-dasharray":z?"4 4":""}));
  svg.appendChild(T(p.l-10,y+4,cfg.ft(t),{"text-anchor":"end",fill:C("--muted")}));});
 let last="";for(let i=0;i<n;i++){const yr=String(cfg.x[i]).slice(0,4);
  if(yr!==last){if(+yr%(cfg.xs||3)===0&&i>2&&i<n-2)svg.appendChild(T(X(i),H-11,yr,{"text-anchor":"middle",fill:C("--muted")}));last=yr;}}
 cfg.s.forEach(s=>{let d="";for(let i=0;i<n;i++){const v=s.v[i];if(v==null)continue;
   d+=(d===""?"M":"L")+X(i).toFixed(1)+" "+Y(v).toFixed(1);}
  if(s.fill)svg.appendChild(E("path",{d:d+`L${X(n-1)} ${Y(cfg.lo)} L${X(0)} ${Y(cfg.lo)} Z`,fill:s.c,opacity:.07}));
  svg.appendChild(E("path",{d,fill:"none",stroke:s.c,"stroke-width":s.w||2,"stroke-linejoin":"round","stroke-dasharray":s.dash||""}));
  if(s.lab){const yv=s.v[n-1];svg.appendChild(E("circle",{cx:X(n-1),cy:Y(yv),r:3.5,fill:s.c,stroke:C("--ground"),"stroke-width":2}));
   svg.appendChild(T(X(n-1)+9,Y(yv)+4,s.lab,{fill:s.c,"font-weight":600,"font-size":11.5}));}});
 const hv=E("line",{x1:0,x2:0,y1:p.t,y2:p.t+ih,stroke:C("--muted"),opacity:0});svg.appendChild(hv);
 const dots=cfg.s.map(s=>{const c=E("circle",{r:4,fill:s.c,stroke:C("--ground"),"stroke-width":2,opacity:0});svg.appendChild(c);return c;});
 const hit=E("rect",{x:p.l,y:p.t,width:iw,height:ih,fill:"transparent"});svg.appendChild(hit);
 hit.addEventListener("mousemove",ev=>{const r=svg.getBoundingClientRect(),px=(ev.clientX-r.left)/r.width*W;
  let i=Math.max(0,Math.min(n-1,Math.round((px-p.l)/iw*(n-1))));
  hv.setAttribute("x1",X(i));hv.setAttribute("x2",X(i));hv.setAttribute("opacity",.45);
  let h=`<b>${cfg.x[i]}</b><br>`;cfg.s.forEach((s,k)=>{const v=s.v[i];
   dots[k].setAttribute("cx",X(i));dots[k].setAttribute("cy",Y(v));dots[k].setAttribute("opacity",1);
   h+=`<span style="color:${s.c}">■</span> ${s.n} ${cfg.fv(v)}<br>`;});show(ev.clientX,ev.clientY,h);});
 hit.addEventListener("mouseleave",()=>{hv.setAttribute("opacity",0);dots.forEach(d=>d.setAttribute("opacity",0));hide();});}

function chartDca(){const d=D.dca;if(!d)return;
 const mx=Math.max(...d.port,...d.hs)*1.06,step=Math.pow(10,Math.floor(Math.log10(mx)))/2;
 const ticks=[];for(let t=0;t<=mx;t+=step)ticks.push(t);
 line("cDca",{x:d.dates,lo:0,hi:mx,ticks,ft:v=>v===0?"0":(v/10000).toFixed(0)+"万",
  fv:v=>(v/10000).toFixed(1)+"万",xs:d.xs||2,
  s:[{n:"本组合",v:d.port,c:C("--gold"),w:2.4,fill:1,lab:(d.port[d.port.length-1]/10000).toFixed(1)+"万"},
     ...(d.hs?[{n:"基准",v:d.hs,c:C("--blue"),w:2,lab:(d.hs[d.hs.length-1]/10000).toFixed(1)+"万"}]:[]),
     {n:"本金",v:d.cost,c:C("--muted"),w:1.5,dash:"5 4",lab:(d.cost[d.cost.length-1]/10000).toFixed(1)+"万"}]});}

function chartRoll(){const r=D.roll;if(!r)return;
 const all=r.port.filter(v=>v!=null),lo=Math.min(0,Math.min(...all))-0.01,hi=Math.max(...all)+0.02;
 const ticks=[];for(let t=Math.ceil(lo*33.3)/33.3;t<hi;t+=0.03)ticks.push(Math.round(t*1000)/1000);
 line("cRoll",{x:r.dates,lo,hi,ticks,zero:0,ft:v=>(v*100).toFixed(0)+"%",fv:v=>(v*100).toFixed(2)+"%",xs:2,
  s:[{n:"本组合",v:r.port,c:C("--gold"),w:2.4,lab:"本组合"}]});}

function chartSens(){const S=D.sens;if(!S||!S.rows.length)return;
 const svg=document.getElementById("cSens");if(!svg)return;svg.innerHTML="";
 const rows=S.rows.slice().sort((a,b)=>a.range-b.range);
 const W=1000,H=60+rows.length*40,p={l:100,r:120,t:34,b:30},iw=W-p.l-p.r,ih=H-p.t-p.b;
 svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
 const vals=rows.flatMap(r=>r.v.filter(x=>x!=null));
 const lo=Math.min(0,Math.min(...vals)-0.01),hi=Math.max(...vals)+0.01;
 const X=v=>p.l+(v-lo)/(hi-lo)*iw,bh=ih/rows.length;
 for(let t=Math.ceil(lo*33.3)/33.3;t<hi;t+=0.03){const x=X(t);
  svg.appendChild(E("line",{x1:x,x2:x,y1:p.t-8,y2:p.t+ih,stroke:C("--rule-2")}));
  svg.appendChild(T(x,p.t-15,(t*100).toFixed(0)+"%",{"text-anchor":"middle",fill:C("--muted"),"font-size":10.5}));}
 rows.forEach((r,i)=>{const y=p.t+bh*i+bh/2,isP=r.kind==="portfolio";
  const col=isP?C("--gold"):(r.range>0.03?C("--blue"):C("--muted"));
  if(isP)svg.appendChild(E("rect",{x:p.l-96,y:y-bh/2+3,width:iw+96+114,height:bh-6,fill:C("--gold"),opacity:.055,rx:3}));
  svg.appendChild(T(p.l-12,y+4,r.name,{"text-anchor":"end",fill:isP?C("--gold"):C("--ink-2"),
   "font-family":"var(--ss)","font-size":12.5,"font-weight":isP?600:400}));
  svg.appendChild(E("line",{x1:X(r.lo),x2:X(r.hi),y1:y,y2:y,stroke:col,"stroke-width":isP?5:3.5,
   "stroke-linecap":"round",opacity:isP?1:.55}));
  r.v.forEach((v,k)=>{if(v==null)return;const c=E("circle",{cx:X(v),cy:y,r:isP?5:4,fill:col,
    stroke:C("--ground"),"stroke-width":1.6});
   c.addEventListener("mouseenter",ev=>show(ev.clientX,ev.clientY,`<b>${r.name}</b><br>${S.starts[k]}：${P(v)}`));
   c.addEventListener("mouseleave",hide);svg.appendChild(c);});
  svg.appendChild(T(X(r.hi)+12,y+4,"极差 "+(r.range*100).toFixed(2)+"pp",
   {fill:isP?C("--gold"):C("--muted"),"font-size":11,"font-weight":isP?600:400}));});}

function heat(id,data){const g=document.getElementById(id);if(!g||!data)return;
 const{labels,m}=data,N=labels.length;
 g.style.gridTemplateColumns=`96px repeat(${N}, minmax(58px,1fr))`;g.innerHTML="";
 const c0=document.createElement("div");c0.className="lt";g.appendChild(c0);
 labels.forEach(l=>{const d=document.createElement("div");d.className="lt";d.textContent=l.length>5?l.slice(0,5):l;g.appendChild(d);});
 for(let i=0;i<N;i++){const lb=document.createElement("div");lb.className="lb";lb.textContent=labels[i];g.appendChild(lb);
  for(let j=0;j<N;j++){const v=m[i][j],c=document.createElement("div"),a=Math.min(1,Math.abs(v));
   if(i===j){c.style.background="none";c.style.color=C("--muted");c.style.border="1px solid "+C("--rule-2");}
   else{c.style.background=`color-mix(in srgb, ${v>=0?C("--gold"):C("--blue")} ${(a*58).toFixed(0)}%, ${C("--panel")})`;
    c.style.color=C("--ink");}
   c.textContent=v.toFixed(2);c.title=`${labels[i]} × ${labels[j]} = ${v.toFixed(2)}`;g.appendChild(c);}}}

function matrix(){const M=D.matrix,g=document.getElementById("mx");if(!g||!M)return;
 g.style.display="grid";g.style.gap="2px";g.style.minWidth="620px";
 g.style.gridTemplateColumns=`68px repeat(${M.hor.length}, minmax(58px,1fr))`;g.innerHTML="";
 const cell=(t,s="")=>{const d=document.createElement("div");d.textContent=t;
  d.setAttribute("style","height:32px;display:grid;place-items:center;font-family:var(--sm);font-size:10.5px;border-radius:2px;font-variant-numeric:tabular-nums;"+s);return d;};
 const head=t=>cell(t,`height:24px;font-family:var(--ss);font-size:10.5px;color:${C("--muted")};background:none;`);
 const col=v=>v==null?C("--rule-3"):(v>=0
   ?`color-mix(in srgb, ${C("--gold")} ${(Math.min(1,v/0.18)*62).toFixed(0)}%, ${C("--panel")})`
   :`color-mix(in srgb, ${C("--neg")} ${(Math.min(1,-v/0.20)*70).toFixed(0)}%, ${C("--panel")})`);
 g.appendChild(head("起投年"));M.hor.forEach(h=>g.appendChild(head(h+"年")));
 M.years.forEach((y,ri)=>{if(M.vals[ri].every(v=>v==null))return;
  g.appendChild(cell(y,`font-family:var(--ss);font-size:11px;color:${C("--ink-2")};background:none;justify-content:end;padding-right:8px;`));
  M.vals[ri].forEach((v,ci)=>{const d=cell(v==null?"—":(v*100).toFixed(1)+"%",
    `background:${col(v)};color:${v==null?C("--muted"):C("--ink")};${v!=null&&v<0?"font-weight:600;":""}`);
   if(v!=null)d.title=`${y} 年起投，持有 ${M.hor[ci]} 年：${P(v)}`;g.appendChild(d);});});}

function draw(){chartDca();chartRoll();chartSens();heat("corr",D.corr);matrix();}
draw();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",draw);
new MutationObserver(draw).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
addEventListener("resize",()=>{clearTimeout(window._t);window._t=setTimeout(draw,180);});
"""
