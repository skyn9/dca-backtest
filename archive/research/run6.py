# -*- coding: utf-8 -*-
"""实盘窗口(2013-08~2026-09, 13.1y, 全部真实基金复权净值)：加入黄金/港股后的最优组合"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(7)
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
AS=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
R=B[AS].dropna().pct_change().dropna()
print(f"实盘窗口 {R.index.min().date()} ~ {R.index.max().date()}  n={len(R)} 月  ({len(R)/12:.1f}年)")
print("注：净值已含全部管理费/托管费/汇率/跟踪误差，无需再扣费\n")

def ev(w,H=60,R_=None):
    Rx=R if R_ is None else R_
    pr=(Rx*np.array(w)).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    if len(i)==0: return None
    return dict(n=len(i),med=i.median(),p10=i.quantile(.10),mn=i.min(),loss=(i<0).mean(),
                mdd=rd["maxdd"].min())

print("="*104); print("【黄金的边际贡献】同一组合，加/不加黄金对比 (滚动5年定投)")
PAIRS=[("均衡组合 不含黄金", dict(zip(AS,[.30,.05,.05,.10,.20,.20,.00,.10]))),
       ("均衡组合 含黄金10%", dict(zip(AS,[.27,.04,.04,.09,.18,.18,.10,.10]))),
       ("均衡组合 含黄金15%", dict(zip(AS,[.25,.04,.04,.08,.17,.17,.15,.10]))),
       ("均衡组合 含黄金20%", dict(zip(AS,[.24,.03,.03,.08,.16,.16,.20,.10])))]
print(f"{'组合':<24}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'最大浮亏':>10}")
for nm,w in PAIRS:
    r=ev([w[a] for a in AS])
    print(f"{nm:<24}{r['med']*100:>8.2f}%{r['p10']*100:>8.2f}%{r['mn']*100:>8.2f}%{r['loss']*100:>7.1f}%{r['mdd']*100:>9.1f}%")

print("\n"+"="*104); print("【实盘窗口 随机搜索最优权重】目标: max 5年定投IRR的10%分位")
def valid(w):
    d=dict(zip(AS,w))
    cn=d["A股红利"]+d["A股沪深300"]+d["A股中证500"]
    ov=d["美股标普500"]+d["美股纳指100"]
    return (max(w)<=.35 and d["债券"]>=.05 and cn>=.20 and ov<=.45 and d["黄金"]<=.25)
best=[];t0=time.time()
for _ in range(6000):
    w=rng.dirichlet(np.ones(len(AS))*0.9)
    if not valid(w): continue
    r=ev(w)
    if r: best.append((r["p10"],r["med"],r["mn"],r["loss"],w))
best.sort(key=lambda x:-x[0])
print(f"有效样本 {len(best)}  耗时{time.time()-t0:.0f}s")
print(f"{'p10':>7}{'中位':>7}{'最差':>7}  "+"".join(f"{a[:6]:>8}" for a in AS))
for p,m,mn,lp,w in best[:10]:
    print(f"{p*100:6.2f}%{m*100:6.2f}%{mn*100:6.2f}%  "+"".join(f"{x*100:7.1f}%" for x in w))
top=np.array([b[4] for b in best[:80]])
print("\n【Top80 平均权重】")
for a,v,s in zip(AS, top.mean(0), top.std(0)): print(f"  {a:12s} {v*100:5.1f}%  ±{s*100:.1f}")
np.save(f"{ROOT}/data/opt_top_fund.npy", top)
