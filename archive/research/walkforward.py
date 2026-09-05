# -*- coding: utf-8 -*-
"""样本外检验：用历史前段优化权重，在后段（模型从未见过）验证。
   这是判断"权重是真规律还是过拟合"的黄金标准。"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(2027)
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
RH=M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12
print(f"可用窗口 {R.index.min().date()} ~ {R.index.max().date()}  {len(R)}月\n")

def dca_irr(r, H=None, buy=0.0012):
    """对一段收益率序列做全程定投，返回 IRR"""
    p=(1+r).cumprod(); cf=[]; units=0.0
    v=p.values
    for t in range(len(v)-1):
        units += 1000*(1-buy)/v[t]; cf.append(1000)
    return E.xirr_monthly(cf, units*v[-1])

def opt(Rtr, H, n_iter=3500):
    """在训练段上优化：最大化滚动H月定投IRR的10%分位；训练段太短则用全程IRR"""
    def score(w):
        pr=(Rtr*w).sum(axis=1)
        if len(pr) > H+12:
            p=pd.DataFrame({"P":(1+pr).cumprod()})
            rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
            i=rd["irr"].dropna()
            return i.quantile(.10) if len(i) else -9
        return dca_irr(pr)
    def valid(w):
        d=dict(zip(AS,w))
        cn=d["A股红利"]+d["A股中证500"]; ov=d["美股标普500(人民币)"]+d["美股纳斯达克(人民币)"]
        return (max(w)<=.35 and d["债券中证全债"]>=.08 and cn>=.20 and ov<=.45 and d["黄金AU0"]<=.25)
    best=[]
    for _ in range(n_iter):
        w=rng.dirichlet(np.ones(len(AS))*0.9)
        if not valid(w): continue
        best.append((score(w),w))
    best.sort(key=lambda x:-x[0])
    return np.array([b[1] for b in best[:40]]).mean(axis=0)

SPLITS=[("2008-01","2015-12","2016-01","2026-09"),
        ("2008-01","2017-12","2018-01","2026-09"),
        ("2005-01","2014-12","2015-01","2026-09"),
        ("2005-01","2016-12","2017-01","2026-09")]
print("="*112)
print("【Walk-Forward 样本外检验】训练段优化权重 → 测试段（模型从未见过）实测")
rows=[]
for tr0,tr1,te0,te1 in SPLITS:
    Rtr=R.loc[tr0:tr1]; Rte=R.loc[te0:te1]; RHte=RH.loc[te0:te1]
    if len(Rtr)<60 or len(Rte)<48: print(f"跳过 {tr0}~{tr1}"); continue
    t0=time.time(); w=opt(Rtr, 60)
    r_opt=dca_irr((Rte*w).sum(axis=1))
    r_pln=dca_irr((Rte*PLAN).sum(axis=1))
    r_eq =dca_irr((Rte*np.ones(len(AS))/len(AS)).sum(axis=1))
    r_hs =dca_irr(RHte)
    # 训练段内的表现（对照，看有多少是"回头看"的幻觉）
    in_opt=dca_irr((Rtr*w).sum(axis=1)); in_pln=dca_irr((Rtr*PLAN).sum(axis=1))
    print(f"\n训练 {tr0}~{tr1} ({len(Rtr)}月) → 测试 {te0}~{te1} ({len(Rte)}月)   [{time.time()-t0:.0f}s]")
    print("  训练段最优权重: " + "  ".join(f"{s}{v*100:.0f}%" for s,v in zip(SH,w)))
    print(f"  {'':22s}{'训练段内IRR':>12}{'测试段IRR':>12}{'衰减':>9}")
    print(f"  {'训练段最优权重':22s}{in_opt*100:11.2f}%{r_opt*100:11.2f}%{(r_opt-in_opt)*100:+8.2f}")
    print(f"  {'★本方案(固定权重)':22s}{in_pln*100:11.2f}%{r_pln*100:11.2f}%{(r_pln-in_pln)*100:+8.2f}")
    print(f"  {'等权7资产':22s}{'—':>12}{r_eq*100:11.2f}%")
    print(f"  {'全仓沪深300':22s}{'—':>12}{r_hs*100:11.2f}%")
    rows.append(dict(tr=f"{tr0[:4]}-{tr1[:4]}",te=f"{te0[:4]}-{te1[:4]}",w=w,
                     opt_in=in_opt,opt_out=r_opt,pln_out=r_pln,eq_out=r_eq,hs_out=r_hs))

print("\n"+"="*112); print("【汇总】样本外(测试段)定投 IRR")
print(f"{'训练→测试':<22}{'训练段最优':>12}{'★本方案':>11}{'等权':>10}{'沪深300':>11}{'最优-本方案':>13}")
for r in rows:
    print(f"{r['tr']}→{r['te']:<12}{r['opt_out']*100:11.2f}%{r['pln_out']*100:10.2f}%{r['eq_out']*100:9.2f}%"
          f"{r['hs_out']*100:10.2f}%{(r['opt_out']-r['pln_out'])*100:+12.2f}")
o=np.mean([r['opt_out'] for r in rows]); p=np.mean([r['pln_out'] for r in rows])
e=np.mean([r['eq_out'] for r in rows]); h=np.mean([r['hs_out'] for r in rows])
print(f"{'平均':<22}{o*100:11.2f}%{p*100:10.2f}%{e*100:9.2f}%{h*100:10.2f}%{(o-p)*100:+12.2f}")
print(f"\n权重稳定性（各训练段最优权重的标准差）:")
W=np.array([r['w'] for r in rows])
for s,m,sd,pl in zip(SH,W.mean(0),W.std(0),PLAN):
    print(f"  {s:10s} 训练均值{m*100:5.1f}% ±{sd*100:4.1f}   本方案{pl*100:5.0f}%   偏离{(pl-m)*100:+5.1f}pp")
