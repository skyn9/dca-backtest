# -*- coding: utf-8 -*-
"""权重优化：目标=最大化滚动10年定投IRR的10%分位(下行保护)，带经济含义约束。"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
rng=np.random.default_rng(42)
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
FEE={"A股沪深300":0.0020,"A股中证500":0.0020,"A股红利":0.0020,"A股上证50":0.0020,
     "A股中证1000":0.0020,"债券中证全债":0.0030,"美股标普500(人民币)":0.0065,"美股纳斯达克(人民币)":0.0065}
ASSETS=["A股红利","A股沪深300","A股中证500","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
R = A[ASSETS].pct_change().dropna() - np.array([FEE[c] for c in ASSETS])/12.0

def rd_stats(w, H=120):
    pr=(R*w).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px, pd.Series({"P":1.0}), H, annual_fee=None, buy_fee=0.0012)
    i=rd["irr"].dropna()
    return i.quantile(.10), i.median(), i.min(), (i<0).mean()

# 约束: 单资产<=35%; 债>=10%; A股合计>=25%; 海外合计<=50%
def valid(w):
    d=dict(zip(ASSETS,w))
    cn=d["A股红利"]+d["A股沪深300"]+d["A股中证500"]
    ov=d["美股标普500(人民币)"]+d["美股纳斯达克(人民币)"]
    return (max(w)<=0.35 and d["债券中证全债"]>=0.10 and cn>=0.25 and ov<=0.50)

t0=time.time(); best=[]
N=4000; cnt=0
for _ in range(N):
    w=rng.dirichlet(np.ones(len(ASSETS))*0.9)
    if not valid(w): continue
    cnt+=1
    p10,med,mn,lp=rd_stats(w)
    best.append((p10,med,mn,lp,w))
best.sort(key=lambda x:-x[0])
print(f"有效采样 {cnt}/{N}   耗时{time.time()-t0:.0f}s")
print("\n【按 10年定投IRR的10%分位 排序 · Top12】")
print(f"{'p10':>7}{'中位':>7}{'最差':>7}{'亏损率':>7}   " + "".join(f"{a[:8]:>10}" for a in ASSETS))
for p10,med,mn,lp,w in best[:12]:
    print(f"{p10*100:6.2f}%{med*100:6.2f}%{mn*100:6.2f}%{lp*100:6.1f}%   " + "".join(f"{x*100:9.1f}%" for x in w))
print("\n【最差12名 对照】")
for p10,med,mn,lp,w in best[-6:]:
    print(f"{p10*100:6.2f}%{med*100:6.2f}%{mn*100:6.2f}%{lp*100:6.1f}%   " + "".join(f"{x*100:9.1f}%" for x in w))

top=np.array([b[4] for b in best[:60]])
print("\n【Top60 平均权重（稳健解，避免单点过拟合）】")
for a,v in zip(ASSETS, top.mean(axis=0)): print(f"  {a:22s} {v*100:5.1f}%  (±{top.std(axis=0)[ASSETS.index(a)]*100:.1f})")
np.save(f"{ROOT}/data/opt_top.npy", top)
