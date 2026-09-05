# -*- coding: utf-8 -*-
"""最终组合回测：双窗口验证 + 定投vs一次性 + bootstrap 20年模拟"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"; rng=np.random.default_rng(2026)
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
# 港股红利用保守股息 4%（而非5%）
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
FEE={"A股沪深300":.0020,"A股中证500":.0020,"A股红利":.0020,"债券中证全债":.0030,
     "美股标普500(人民币)":.0065,"美股纳斯达克(人民币)":.0065,"港股红利TR":.0060}
LA=["A股红利","A股沪深300","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
RA=A[LA].pct_change().dropna()-np.array([FEE[c] for c in LA])/12.0

# ---- 最终方案（长窗口版：黄金12%按比例分摊给其他，因长窗口无黄金数据）----
CORE   = dict(zip(LA,[.22,.08,.05,.10,.18,.15,.10]))          # 股90+债10 合计88%（+黄金12%）
CORE_L = {k:v/sum(CORE.values()) for k,v in CORE.items()}      # 长窗口：等比放大到100%
BENCH={
 "全仓沪深300":        dict(zip(LA,[0,1,0,0,0,0,0])),
 "沪深300+债 60/40":  dict(zip(LA,[0,.6,0,0,0,0,.4])),
 "A股宽基均衡":         dict(zip(LA,[.34,.33,.33,0,0,0,0])),
 "全仓纳指100":        dict(zip(LA,[0,0,0,0,0,1,0])),
 "★本方案(股票部分)":    CORE_L,
}
def ev(R,w,H,buy=0.0012):
    pr=(R*np.array([w[c] for c in R.columns])).sum(axis=1)
    px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=buy)
    i=rd["irr"].dropna()
    return dict(n=len(i),med=i.median(),p10=i.quantile(.10),p90=i.quantile(.90),mn=i.min(),
                loss=(i<0).mean(),mdd=rd["maxdd"].median(),wmdd=rd["maxdd"].min(),
                mmul=rd["mult"].median(),wmul=rd["mult"].min())
print("="*118)
print("【最终方案 · 长窗口验证 2005-01~2026-09（21.7年，指数全收益，已扣模拟费率，不含黄金）】")
for H,hn in [(60,"5年"),(120,"10年"),(180,"15年")]:
    print(f"\n--- 定投{hn} ---")
    print(f"{'组合':<22}{'样本':>5}{'中位IRR':>9}{'10%分位':>9}{'90%分位':>9}{'最差':>8}{'亏损率':>7}{'中位浮亏':>9}{'最差浮亏':>9}{'中位终值':>9}")
    for nm,w in BENCH.items():
        r=ev(RA,w,H)
        print(f"{nm:<22}{r['n']:>5}{r['med']*100:>8.2f}%{r['p10']*100:>8.2f}%{r['p90']*100:>8.2f}%"
              f"{r['mn']*100:>7.2f}%{r['loss']*100:>6.1f}%{r['mdd']*100:>8.1f}%{r['wmdd']*100:>8.1f}%{r['mmul']:>8.2f}x")

# ---- 实盘窗口（含黄金，真实净值）----
LB=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
RB=B[LB].dropna().pct_change().dropna()
FULL=dict(zip(LB,[.22,.08,.05,.10,.18,.15,.12,.10]))
BENCH2={"全仓沪深300":dict(zip(LB,[0,1,0,0,0,0,0,0])),
        "沪深300+债60/40":dict(zip(LB,[0,.6,0,0,0,0,0,.4])),
        "★本方案(完整含黄金)":FULL,
        "★本方案 去掉黄金":dict(zip(LB,[.25,.09,.06,.11,.20,.17,.00,.12]))}
print("\n"+"="*118)
print(f"【最终方案 · 实盘验证 {RB.index.min().date()}~{RB.index.max().date()}（{len(RB)/12:.1f}年，真实基金复权净值，港股用恒生指数=保守）】")
for H,hn in [(36,"3年"),(60,"5年"),(120,"10年")]:
    print(f"\n--- 定投{hn} ---")
    print(f"{'组合':<22}{'样本':>5}{'中位IRR':>9}{'10%分位':>9}{'最差':>8}{'亏损率':>7}{'中位浮亏':>9}{'最差浮亏':>9}")
    for nm,w in BENCH2.items():
        r=ev(RB,w,H)
        print(f"{nm:<22}{r['n']:>5}{r['med']*100:>8.2f}%{r['p10']*100:>8.2f}%{r['mn']*100:>7.2f}%"
              f"{r['loss']*100:>6.1f}%{r['mdd']*100:>8.1f}%{r['wmdd']*100:>8.1f}%")
