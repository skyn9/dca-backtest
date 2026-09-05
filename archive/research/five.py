# -*- coding: utf-8 -*-
"""5 只极简版：金额分配 + 主窗口复核"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}

PLANS={
 "7只完整版": {"A股红利":.24,"A股中证500":.06,"港股红利TR":.10,"美股标普500(人民币)":.18,
              "美股纳斯达克(人民币)":.14,"黄金AU0":.13,"债券中证全债":.15},
 "5只·标准(去港股+中证500)": {"A股红利":.28,"美股标普500(人民币)":.17,
              "美股纳斯达克(人民币)":.15,"黄金AU0":.15,"债券中证全债":.25},
 "5只·保留港股(去中证500+纳指)": {"A股红利":.27,"港股红利TR":.13,"美股标普500(人民币)":.28,
              "黄金AU0":.14,"债券中证全债":.18},
 "5只·保留港股(去中证500+标普)": {"A股红利":.26,"港股红利TR":.12,"美股纳斯达克(人民币)":.26,
              "黄金AU0":.15,"债券中证全债":.21},
}
print("【主窗口 2008-01~2026-09 复核】滚动定投，已扣模拟费率与0.12%申购费\n")
print(f"{'方案':<28}{'期限':<6}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'年化波动':>9}{'最大回撤':>9}")
for nm,W in PLANS.items():
    cols=list(W); w=np.array([W[c] for c in cols])
    M=A[cols].dropna(); R=M.pct_change().dropna()-np.array([FEE[c] for c in cols])/12.0
    pr=(R*w).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    cum=(1+pr).cumprod(); mdd=(cum/cum.cummax()-1).min(); vol=pr.std()*np.sqrt(12)
    for H,tag in [(60,"5年"),(120,"10年")]:
        rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
        i=rd["irr"].dropna()
        print(f"{nm if tag=='5年' else '':<28}{tag:<6}{i.median()*100:>8.2f}%{i.quantile(.1)*100:>8.2f}%"
              f"{i.min()*100:>8.2f}%{(i<0).mean()*100:>7.1f}%{rd['maxdd'].median()*100:>8.1f}%"
              f"{vol*100:>8.1f}%{mdd*100:>8.1f}%")
    print()

print("="*96)
print("【每月 2,000 元 · 5只标准版 扣款清单】")
FUND=[("A股红利",  .28,"009051","易方达中证红利ETF联接A","0.20%"),
      ("美股标普500",.17,"017641","摩根标普500指数(QDII)人民币A","0.65%"),
      ("美股纳指100",.15,"016532","嘉实纳斯达克100ETF联接(QDII)A","0.60%"),
      ("黄金",      .15,"008701","华夏黄金ETF联接A","0.20%"),
      ("债券",      .25,"006961","南方中债7-10年国开行债券指数A","0.20%")]
tot=2000; fee=0
print(f"{'资产':<12}{'权重':>6}{'月扣款':>9}{'代码':>9}  {'基金名称':<30}{'年费率':>7}")
for nm,w,code,fn,fr in FUND:
    amt=round(tot*w); fee+=amt*float(fr.strip('%'))/100
    print(f"{nm:<12}{w*100:5.0f}%{amt:>8}元{code:>9}  {fn:<30}{fr:>7}")
print(f"{'合计':<12}{'100%':>6}{tot:>8}元{'':>9}  {'5 只':<30}{fee/tot*100:6.2f}%")
print(f"\n年投入 {tot*12:,} 元 · 年持有成本约 {fee*12:.0f} 元 · 首月申购费约 {tot*0.0012:.1f} 元")
for yrs,r in [(10,.06),(20,.06),(20,.07),(20,.05)]:
    m=tot; k=(1+r)**(1/12)-1
    fv=sum(m*(1+k)**(yrs*12-t) for t in range(yrs*12))
    print(f"  {yrs}年 @{r*100:.0f}%: 投入 {tot*12*yrs:>8,} 元 → 约 {fv:>10,.0f} 元")
