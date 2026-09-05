# -*- coding: utf-8 -*-
"""执行策略研究：定投vs一次性 / 再平衡频率 / 止盈 / A类vsC类 / 定投频率"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
FEE={"A股沪深300":.0020,"A股中证500":.0020,"A股红利":.0020,"债券中证全债":.0030,
     "美股标普500(人民币)":.0065,"美股纳斯达克(人民币)":.0065,"港股红利TR":.0060}
LA=["A股红利","A股沪深300","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
R=A[LA].pct_change().dropna()-np.array([FEE[c] for c in LA])/12.0
W=np.array([.22,.08,.05,.10,.18,.15,.10]); W=W/W.sum()
pr=(R*W).sum(axis=1); PX=pd.DataFrame({"P":(1+pr).cumprod()})
S=pd.Series({"P":1.0})

print("="*100); print("【问题1】定投 vs 一次性投入（同样的总金额）")
print(f"{'期限':<8}{'定投中位IRR':>13}{'一次性中位IRR':>14}{'定投亏损率':>11}{'一次性亏损率':>13}{'定投最差':>10}{'一次性最差':>11}")
for H,hn in [(36,"3年"),(60,"5年"),(120,"10年"),(180,"15年")]:
    rd=E.rolling_dca(PX,S,H,annual_fee=None,buy_fee=0.0012)
    lump=[]
    p=PX["P"].values
    for s in range(0,len(p)-H):
        lump.append((p[s+H]/p[s])**(12/H)-1)
    lump=pd.Series(lump); i=rd["irr"].dropna()
    print(f"{hn:<8}{i.median()*100:>12.2f}%{lump.median()*100:>13.2f}%{(i<0).mean()*100:>10.1f}%"
          f"{(lump<0).mean()*100:>12.1f}%{i.min()*100:>9.2f}%{lump.min()*100:>10.2f}%")

print("\n"+"="*100); print("【问题2】再平衡方式对比（10年定投）")
for mode,lab in [("cashflow","现金流再平衡(新钱补低配,不卖出)"),("annual","年度再平衡(卖高买低)"),("none","不再平衡(躺平)")]:
    rd=E.rolling_dca(PX,S,120,annual_fee=None,buy_fee=0.0012,rebalance=mode)
    i=rd["irr"].dropna()
    print(f"  {lab:<32} 中位IRR={i.median()*100:6.2f}%  10%分位={i.quantile(.1)*100:6.2f}%  最差={i.min()*100:6.2f}%")
# 组合层面再平衡(多资产)才有意义 -> 用多资产版本
print("\n  [多资产版] 组合内部再平衡:")
for mode in ["cashflow","annual","none"]:
    rd=E.rolling_dca(A[LA],pd.Series(dict(zip(LA,W))),120,annual_fee=FEE,buy_fee=0.0012,rebalance=mode)
    i=rd["irr"].dropna()
    lab={"cashflow":"现金流再平衡","annual":"年度再平衡","none":"不再平衡"}[mode]
    print(f"  {lab:<32} 中位IRR={i.median()*100:6.2f}%  10%分位={i.quantile(.1)*100:6.2f}%  最差={i.min()*100:6.2f}%")

print("\n"+"="*100); print("【问题3】A类 vs C类 盈亏平衡（申购费0.12% 一次性 vs 销售服务费0.2%/年）")
for yrs in [1,2,3,5,10,20]:
    a=0.0012; c=0.002*yrs
    print(f"  持有{yrs:>2}年:  A类累计成本={a*100:.2f}%   C类累计成本={c*100:.2f}%   -> {'A类胜' if a<c else 'C类胜'}")

print("\n"+"="*100); print("【问题4】止盈 vs 不止盈（10年定投，触发后清仓转债券再重新定投）")
def dca_tp(px, H, tp=None):
    p=px["P"].values; out=[]
    for s in range(0,len(p)-H):
        units=0.0; cost=0.0; cash=0.0; cf=[]
        for t in range(H):
            units+=1000*(1-0.0012)/p[s+t]; cost+=1000; cf.append(1000)
            v=units*p[s+t+1]
            if tp and cost>0 and (v+cash)/cost-1>=tp:
                cash+=v*(1+0.03)**(1/12); units=0.0     # 止盈转3%年化理财
            elif cash>0: cash*= (1+0.03)**(1/12)
        fv=units*p[s+H]+cash
        out.append(E.xirr_monthly(cf,fv))
    return pd.Series(out).dropna()
for tp,lab in [(None,"不止盈"),(0.30,"浮盈30%止盈"),(0.50,"浮盈50%止盈"),(1.00,"浮盈100%止盈")]:
    r=dca_tp(PX,120,tp)
    print(f"  {lab:<14} 中位IRR={r.median()*100:6.2f}%  10%分位={r.quantile(.1)*100:6.2f}%  最差={r.min()*100:6.2f}%")
