# -*- coding: utf-8 -*-
"""起点敏感性：同一方案在多个窗口下的结论是否一致"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
PLAN={"A股红利":.24,"A股中证500":.06,"港股红利":.10,"美股标普500":.18,"美股纳指100":.14,"黄金":.13,"债券":.15}
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
COL={"A股红利":"A股红利","A股中证500":"A股中证500","港股红利":"港股红利TR",
     "美股标普500":"美股标普500(人民币)","美股纳指100":"美股纳斯达克(人民币)","黄金":"黄金AU0","债券":"债券中证全债"}
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}
cols=[COL[k] for k in PLAN]; w=np.array([PLAN[k] for k in PLAN])

print("【A股起点效应】同一指数，不同起点的年化收益")
print(f"{'指数':<16}" + "".join(f"{s:>12}" for s in ["2005-01起","2008-01起","2011-01起","2015-06起"]))
for c in ["A股红利","A股中证500","A股沪深300","美股标普500(人民币)","黄金AU0"]:
    row=f"{c:<16}"
    for st in ["2005-01","2008-01","2011-01","2015-06"]:
        s=A[c].dropna(); s=s[s.index>=st]
        if len(s)<24: row+=f"{'—':>12}"; continue
        yy=(len(s)-1)/12; row+=f"{((s.iloc[-1]/s.iloc[0])**(1/yy)-1)*100:11.2f}%"
    print(row)

print("\n" + "="*108)
print("【方案在不同窗口下的稳健性】滚动定投，月投，申购费0.12%，已扣模拟年费")
WIN=[("2005-01 起 · 21.7年 · 无黄金(权重等比放大)","2005-01",False),
     ("2008-01 起 · 18.7年 · 含黄金","2008-01",True),
     ("2011-01 起 · 15.7年 · 含黄金","2011-01",True),
     ("2013-09 起 · 13.1年 · 含黄金","2013-09",True)]
for tag,st,gold in WIN:
    use=[c for c in cols if gold or c!="黄金AU0"]
    ww=np.array([PLAN[k] for k in PLAN if gold or COL[k]!="黄金AU0"]); ww=ww/ww.sum()
    M=A[use+["A股沪深300"]].dropna(); M=M[M.index>=st]
    if len(M)<80: print(f"\n--- {tag}: 数据不足 ---"); continue
    R=M[use].pct_change().dropna()-np.array([FEE[c] for c in use])/12.0
    px=pd.DataFrame({"P":(1+(R*ww).sum(axis=1)).cumprod()})
    hs=pd.DataFrame({"P":(1+(M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12)).cumprod()})
    print(f"\n--- {tag}  ({len(M)}月) ---")
    print(f"{'期限':<6}{'方案':<12}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'样本':>6}")
    for H,t2 in [(60,"5年"),(120,"10年")]:
        if len(M)-H < 12: continue
        for nm,p in [("本方案",px),("沪深300",hs)]:
            rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
            i=rd["irr"].dropna()
            print(f"{t2:<6}{nm:<12}{i.median()*100:>8.2f}%{i.quantile(.1)*100:>8.2f}%{i.min()*100:>8.2f}%"
                  f"{(i<0).mean()*100:>7.1f}%{rd['maxdd'].median()*100:>8.1f}%{len(i):>6}")

print("\n" + "="*108); print("【黄金的边际贡献：是否稳健？】10年定投，同窗口内含/不含黄金对比")
print(f"{'窗口':<26}{'含黄金中位':>11}{'无黄金中位':>11}{'差':>8}{'含黄金最差':>11}{'无黄金最差':>11}{'含浮亏':>9}{'无浮亏':>9}")
for tag,st,_ in WIN[1:]:
    M=A[cols+["A股沪深300"]].dropna(); M=M[M.index>=st]
    if len(M)<132: continue
    R=M[cols].pct_change().dropna()-np.array([FEE[c] for c in cols])/12.0
    wg=w.copy(); wn=w.copy(); wn[list(PLAN).index("黄金")]=0; wn=wn/wn.sum()
    res=[]
    for ww2 in [wg,wn]:
        p=pd.DataFrame({"P":(1+(R*ww2).sum(axis=1)).cumprod()})
        rd=E.rolling_dca(p,pd.Series({"P":1.0}),120,annual_fee=None,buy_fee=0.0012)
        i=rd["irr"].dropna(); res.append((i.median(),i.min(),rd["maxdd"].median()))
    print(f"{tag[:24]:<26}{res[0][0]*100:10.2f}%{res[1][0]*100:10.2f}%{(res[0][0]-res[1][0])*100:+7.2f}"
          f"{res[0][1]*100:10.2f}%{res[1][1]*100:10.2f}%{res[0][2]*100:8.1f}%{res[1][2]*100:8.1f}%")
