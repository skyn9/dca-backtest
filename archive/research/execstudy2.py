# -*- coding: utf-8 -*-
"""实操研究：定投日期/频率/递增/估值加权/再平衡阈值"""
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
# 用日频指数合成组合（做日期效应必须日频）
import glob
D={}
for c,f in [("A股红利","csidx_H00922"),("A股中证500","csidx_H00905"),("债券","csidx_H11001")]:
    pass
# 日频：直接用已缓存的日频基金净值合成（更真实）
FUND={"A股红利":"100032","A股中证500":"161017","港股红利":"000071","美股标普500":"050025",
      "美股纳指100":"160213","黄金":"000216","债券":"110017"}
W={"A股红利":.24,"A股中证500":.06,"港股红利":.10,"美股标普500":.18,"美股纳指100":.14,"黄金":.13,"债券":.15}
ser={}
for k,c in FUND.items():
    f,_=fetch.fund_hist(c); ser[k]=f.set_index("date")["adj"]
Dd=pd.DataFrame(ser).dropna()
print(f"日频合成窗口 {Dd.index.min().date()} ~ {Dd.index.max().date()}  {len(Dd)}个交易日 ({len(Dd)/244:.1f}年)")
r=Dd.pct_change().fillna(0)
port=(1+(r*pd.Series(W)).sum(axis=1)).cumprod()

def dca_days(px, day_rule, amount=1000, buy=0.0012):
    """day_rule: ('mday',N) 每月第N个交易日 / ('week',w) 每周w / ('biweek',) """
    idx=px.index; buys=[]
    if day_rule[0]=="mday":
        N=day_rule[1]
        for (y,m),g in px.groupby([idx.year,idx.month]):
            if len(g)>=N: buys.append(g.index[N-1])
    elif day_rule[0]=="cal":   # 每月N号之后第一个交易日
        N=day_rule[1]
        for (y,m),g in px.groupby([idx.year,idx.month]):
            c=[d for d in g.index if d.day>=N]
            buys.append(c[0] if c else g.index[-1])
    elif day_rule[0]=="week":
        w=day_rule[1]
        seen=set()
        for d in idx:
            k=(d.isocalendar().year,d.isocalendar().week)
            if k in seen: continue
            if d.weekday()==w or (k not in seen and d.weekday()>w):
                buys.append(d); seen.add(k)
    units=0.0; cf=[]
    for d in buys:
        units += amount*(1-buy)/px.loc[d]; cf.append(amount)
    return E.xirr_monthly_days(cf, buys, units*px.iloc[-1], px.index[-1]) if hasattr(E,'xirr_monthly_days') else (units*px.iloc[-1], sum(cf), len(cf))

print("\n【1】每月第几个交易日买入（日期效应）")
base=None
for N in [1,2,3,5,8,10,12,15,18,20]:
    fv,cost,cnt=dca_days(port,("mday",N))
    if base is None: base=fv
    print(f"  每月第{N:2d}个交易日: 期末{fv:,.0f} 投入{cost:,.0f} 倍数{fv/cost:.4f}  相对第1日 {(fv/base-1)*100:+.3f}%  ({cnt}次)")

print("\n【2】自然日规则（发薪日常见）")
for N in [1,5,10,15,20,25]:
    fv,cost,cnt=dca_days(port,("cal",N))
    print(f"  每月{N:2d}号后首个交易日: 倍数{fv/cost:.4f}  ({cnt}次)")

print("\n【3】频率：周投 vs 月投（同等总投入）")
fvm,cm,nm_=dca_days(port,("mday",1),amount=1000)
for w,lab in [(0,"周一"),(2,"周三"),(4,"周五")]:
    fvw,cw,nw=dca_days(port,("week",w),amount=1000*12/52)
    print(f"  每{lab}投: 倍数{fvw/cw:.4f} ({nw}次) | 月投倍数{fvm/cm:.4f} ({nm_}次)  差{(fvw/cw-fvm/cm)*100:+.3f}pp")
