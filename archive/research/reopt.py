# -*- coding: utf-8 -*-
"""用 2008 起含黄金窗口重做权重优化，检验权重是否被 2005 起点带偏"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(11)
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
AS=["A股红利","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","黄金AU0","债券中证全债"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030}
SHORT=["红利","中证500","港股红利","标普500","纳指100","黄金","债券"]

def run(st, H, label):
    M=A[AS].dropna(); M=M[M.index>=st]
    R=M.pct_change().dropna()-np.array([FEE[c] for c in AS])/12.0
    def ev(w):
        p=pd.DataFrame({"P":(1+(R*w).sum(axis=1)).cumprod()})
        rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
        i=rd["irr"].dropna()
        return (i.quantile(.1), i.median(), i.min()) if len(i) else None
    def valid(w):
        d=dict(zip(AS,w))
        cn=d["A股红利"]+d["A股中证500"]; ov=d["美股标普500(人民币)"]+d["美股纳斯达克(人民币)"]
        return (max(w)<=.35 and d["债券中证全债"]>=.08 and cn>=.20 and ov<=.45 and d["黄金AU0"]<=.25)
    best=[]; t0=time.time()
    for _ in range(5000):
        w=rng.dirichlet(np.ones(len(AS))*0.9)
        if not valid(w): continue
        r=ev(w)
        if r: best.append((r[0],r[1],r[2],w))
    best.sort(key=lambda x:-x[0])
    top=np.array([b[3] for b in best[:60]])
    print(f"\n--- {label}  ({len(M)}月, 滚动{H//12}年, 有效样本{len(best)}, {time.time()-t0:.0f}s) ---")
    print("  最优解 p10=%.2f%% 中位=%.2f%% 最差=%.2f%%"%(best[0][0]*100,best[0][1]*100,best[0][2]*100))
    print("  Top60均值权重: " + "  ".join(f"{s}{v*100:.0f}%" for s,v in zip(SHORT, top.mean(0))))
    return top.mean(0)

w08=run("2008-01",120,"2008-01 起 · 18.7年 · 含黄金")
w11=run("2011-01",120,"2011-01 起 · 15.7年 · 含黄金")
print("\n" + "="*94)
print("【与我采用的方案权重对比】")
PLAN=[.24,.06,.10,.18,.14,.13,.15]
print(f"{'资产':<10}{'2008起优化':>11}{'2011起优化':>11}{'我的方案':>10}{'偏离':>8}")
for s,a,b,p in zip(SHORT,w08,w11,PLAN):
    avg=(a+b)/2
    print(f"{s:<10}{a*100:10.1f}%{b*100:10.1f}%{p*100:9.0f}%{(p-avg)*100:+7.1f}")
