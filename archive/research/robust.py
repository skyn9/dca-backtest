# -*- coding: utf-8 -*-
"""稳健性三件套：①权重扰动 ②Block Bootstrap ③蒙特卡洛前瞻20年"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(31415)
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
AS=["A股红利","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","黄金AU0","债券中证全债"]
SH=["红利","中证500","港股红利","标普500","纳指100","黄金","债券"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}
PLAN=np.array([.24,.06,.10,.18,.14,.13,.15])
M=A[AS+["A股沪深300"]].dropna()
R=M[AS].pct_change().dropna()-np.array([FEE[c] for c in AS])/12.0
RH=(M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12)
print(f"窗口 {R.index.min().date()}~{R.index.max().date()} {len(R)}月\n")

def stats(pr,H=120):
    p=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    return i.median(), i.quantile(.1), i.min(), float((i<0).mean()), rd["maxdd"].median()

print("="*104); print("【① 权重扰动敏感性】随机扰动权重 ±X pp，看结果分布（检验权重是否必须精确）")
base=stats((R*PLAN).sum(axis=1))
print(f"  基准(本方案精确权重): 10年定投中位={base[0]*100:.2f}%  10%分位={base[1]*100:.2f}%  最差={base[2]*100:.2f}%")
for pert in [0.03,0.05,0.08]:
    meds=[];mins=[]
    for _ in range(200):
        w=PLAN+rng.uniform(-pert,pert,len(PLAN))
        w=np.clip(w,0.01,None); w=w/w.sum()
        m=stats((R*w).sum(axis=1)); meds.append(m[0]); mins.append(m[2])
    meds=np.array(meds); mins=np.array(mins)
    print(f"  扰动±{pert*100:.0f}pp (200次): 中位IRR {meds.min()*100:5.2f}%~{meds.max()*100:5.2f}% (均值{meds.mean()*100:.2f}%, 标准差{meds.std()*100:.2f})"
          f" | 最差IRR均值{mins.mean()*100:.2f}%  全部>0: {bool((mins>0).all())}")

print("\n"+"="*104); print("【② Block Bootstrap】按12月块重采样保留自相关，生成5000条历史路径")
def block_boot(Rm, n_paths=5000, L=12, horizon=120):
    arr=Rm.values; T=len(arr); nb=int(np.ceil(horizon/L))
    out=np.empty(n_paths)
    for k in range(n_paths):
        idx=rng.integers(0,T-L,nb)
        seq=np.concatenate([arr[i:i+L] for i in idx])[:horizon]
        units=0.0; p=np.cumprod(1+seq); cf=[1000.0]*horizon
        v=np.concatenate([[1.0],p])
        for t in range(horizon): units+=1000*0.9988/v[t]
        out[k]=E.xirr_monthly(cf, units*v[horizon])
    return pd.Series(out).dropna()
for nm,pr in [("★本方案",(R*PLAN).sum(axis=1)),("全仓沪深300",RH),
              ("等权7资产",(R*(np.ones(7)/7)).sum(axis=1))]:
    t0=time.time(); b=block_boot(pr.to_frame("x"),3000)
    print(f"  {nm:12s} 中位={b.median()*100:6.2f}%  5%分位={b.quantile(.05)*100:6.2f}%  95%分位={b.quantile(.95)*100:6.2f}%"
          f"  亏损概率={(b<0).mean()*100:5.2f}%  ({time.time()-t0:.0f}s)")

print("\n"+"="*104); print("【③ 蒙特卡洛前瞻 20 年】保留资产间相关性，用历史均值/协方差模拟未来")
mu=R.mean().values; cov=R.cov().values
print("  各资产历史月均收益(年化): " + "  ".join(f"{s}{(1+m)**12*100-100:.1f}%" for s,m in zip(SH,mu)))
def mc(mu_, cov_, w, months=240, n_paths=8000):
    L=np.linalg.cholesky(cov_+np.eye(len(mu_))*1e-12)
    out=np.empty(n_paths)
    for k in range(n_paths):
        z=rng.standard_normal((months,len(mu_)))
        r=mu_+z@L.T
        pr=(r*w).sum(axis=1)
        v=np.concatenate([[1.0],np.cumprod(1+pr)])
        units=sum(1000*0.9988/v[t] for t in range(months))
        out[k]=E.xirr_monthly([1000.0]*months, units*v[months])
    return pd.Series(out).dropna()
SCEN=[("历史均值原样",1.0),("股票收益打8折",0.8),("股票收益打6折",0.6)]
for tag,f in SCEN:
    mu2=mu.copy()
    for i,c in enumerate(AS):
        if c!="债券中证全债": mu2[i]=mu[i]*f
    for nm,w in [("★本方案",PLAN),("全仓沪深300",None)]:
        if w is None:
            muh=RH.mean(); sdh=RH.std()
            o=[]
            for k in range(4000):
                r=muh+rng.standard_normal(240)*sdh
                if f!=1.0: r=r*f
                v=np.concatenate([[1.0],np.cumprod(1+r)])
                units=sum(1000*0.9988/v[t] for t in range(240))
                o.append(E.xirr_monthly([1000.0]*240, units*v[240]))
            s=pd.Series(o).dropna()
        else:
            s=mc(mu2,cov,w)
        print(f"  [{tag:12s}] {nm:10s} 20年定投IRR 中位={s.median()*100:6.2f}%  5%分位={s.quantile(.05)*100:6.2f}%"
              f"  95%分位={s.quantile(.95)*100:6.2f}%  亏损概率={(s<0).mean()*100:.2f}%")
