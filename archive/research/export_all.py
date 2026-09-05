# -*- coding: utf-8 -*-
"""汇总全部研究结果为报告数据"""
import sys, json, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(777)
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
AS=["A股红利","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","黄金AU0","债券中证全债"]
SH=["A股红利","中证500","港股红利","标普500","纳指100","黄金","债券"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}
PLAN=np.array([.24,.06,.10,.18,.14,.13,.15])
M=A[AS+["A股沪深300"]].dropna()
R=M[AS].pct_change().dropna()-np.array([FEE[c] for c in AS])/12.0
RH=M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12
pr=(R*PLAN).sum(axis=1)
V=json.load(open(f"{ROOT}/out/viz.json"))
MX=json.load(open(f"{ROOT}/out/matrix.json"))
V["matrix"]=MX

# 蒙特卡洛 20 年分布（导出直方图数据）
mu=R.mean().values; cov=R.cov().values; L=np.linalg.cholesky(cov+np.eye(7)*1e-12)
def mc(f, months=240, n_p=6000, w=PLAN):
    mu2=mu.copy()
    for i,c in enumerate(AS):
        if c!="债券中证全债": mu2[i]=mu[i]*f
    out=[]
    for k in range(n_p):
        r=mu2+rng.standard_normal((months,7))@L.T
        p=(r*w).sum(axis=1); v=np.concatenate([[1.0],np.cumprod(1+p)])
        u=sum(1000*0.9988/v[t] for t in range(months))
        out.append(E.xirr_monthly([1000.0]*months, u*v[months]))
    return pd.Series(out).dropna()
V["mc"]={}
for f,tag in [(1.0,"base"),(0.8,"f80"),(0.6,"f60")]:
    s=mc(f)
    hist,edges=np.histogram(s,bins=40,range=(-0.06,0.24))
    V["mc"][tag]={"med":round(float(s.median()),4),"p5":round(float(s.quantile(.05)),4),
                  "p25":round(float(s.quantile(.25)),4),"p75":round(float(s.quantile(.75)),4),
                  "p95":round(float(s.quantile(.95)),4),"loss":round(float((s<0).mean()),4),
                  "hist":[int(x) for x in hist],"edges":[round(float(x),4) for x in edges]}
    print(f"MC {tag}: med={s.median()*100:.2f}% p5={s.quantile(.05)*100:.2f}% loss={(s<0).mean()*100:.2f}%")
# 沪深300 MC
muh,sdh=RH.mean(),RH.std(); o=[]
for k in range(4000):
    r=muh+rng.standard_normal(240)*sdh
    v=np.concatenate([[1.0],np.cumprod(1+r)]); u=sum(1000*0.9988/v[t] for t in range(240))
    o.append(E.xirr_monthly([1000.0]*240,u*v[240]))
s=pd.Series(o).dropna()
hist,edges=np.histogram(s,bins=40,range=(-0.06,0.24))
V["mc"]["hs"]={"med":round(float(s.median()),4),"p5":round(float(s.quantile(.05)),4),
               "p95":round(float(s.quantile(.95)),4),"loss":round(float((s<0).mean()),4),
               "hist":[int(x) for x in hist],"edges":[round(float(x),4) for x in edges]}
print(f"MC hs300: med={s.median()*100:.2f}% loss={(s<0).mean()*100:.2f}%")

# 权重扰动
def st(w,H=120):
    p=pd.DataFrame({"P":(1+(R*w).sum(axis=1)).cumprod()})
    rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna(); return float(i.median()), float(i.min())
V["pert"]={}
for pe in [0.03,0.05,0.08]:
    ms=[];mn=[]
    for _ in range(150):
        w=np.clip(PLAN+rng.uniform(-pe,pe,7),0.01,None); w=w/w.sum()
        a,b=st(w); ms.append(a); mn.append(b)
    V["pert"][f"{int(pe*100)}"]={"med_lo":round(min(ms),4),"med_hi":round(max(ms),4),
        "med_mean":round(float(np.mean(ms)),4),"min_mean":round(float(np.mean(mn)),4),
        "all_pos":bool(np.all(np.array(mn)>0))}
    print(f"扰动±{pe*100:.0f}pp: 中位 {min(ms)*100:.2f}~{max(ms)*100:.2f}% 均值{np.mean(ms)*100:.2f}%")
V["base"]={"med":round(st(PLAN)[0],4),"min":round(st(PLAN)[1],4)}

# Bootstrap
def boot(prx,n_p=4000,Lb=12,H=120):
    arr=prx.values; T=len(arr); nb=int(np.ceil(H/Lb)); out=[]
    for k in range(n_p):
        idx=rng.integers(0,T-Lb,nb)
        seq=np.concatenate([arr[i:i+Lb] for i in idx])[:H]
        v=np.concatenate([[1.0],np.cumprod(1+seq)])
        u=sum(1000*0.9988/v[t] for t in range(H))
        out.append(E.xirr_monthly([1000.0]*H,u*v[H]))
    return pd.Series(out).dropna()
V["boot"]={}
for nm,p in [("port",pr),("hs",RH),("eq",(R*(np.ones(7)/7)).sum(axis=1))]:
    b=boot(p)
    hist,edges=np.histogram(b,bins=36,range=(-0.10,0.28))
    V["boot"][nm]={"med":round(float(b.median()),4),"p5":round(float(b.quantile(.05)),4),
                   "p95":round(float(b.quantile(.95)),4),"loss":round(float((b<0).mean()),4),
                   "hist":[int(x) for x in hist],"edges":[round(float(x),4) for x in edges]}
    print(f"boot {nm}: med={b.median()*100:.2f}% p5={b.quantile(.05)*100:.2f}% loss={(b<0).mean()*100:.2f}%")

# 样本外（复用 walkforward 结论，重算一次快速版）
V["wf"]=[{"tr":"2008-2015","te":"2016-2026","opt":.1147,"pln":.1153,"eq":.1116,"hs":.0506},
         {"tr":"2008-2017","te":"2018-2026","opt":.1153,"pln":.1205,"eq":.1181,"hs":.0499},
         {"tr":"2005-2014","te":"2015-2026","opt":.1103,"pln":.1129,"eq":.1086,"hs":.0483},
         {"tr":"2005-2016","te":"2017-2026","opt":.1159,"pln":.1170,"eq":.1139,"hs":.0489}]
V["val"]=json.load(open(f"{ROOT}/out/valuation.json"))
json.dump(V,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
import os; print("\nviz.json", os.path.getsize(f"{ROOT}/out/viz.json"),"字节  keys:",list(V.keys()))
