# -*- coding: utf-8 -*-
"""递增定投 / 逆势加码 / 再平衡阈值 —— 用多窗口验证，避免单路径噪音"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
AS=["A股红利","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","黄金AU0","债券中证全债"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030}
PLAN=np.array([.24,.06,.10,.18,.14,.13,.15])
R=A[AS].dropna().pct_change().dropna()-np.array([FEE[c] for c in AS])/12.0
pr=(R*PLAN).sum(axis=1); v_all=np.concatenate([[1.0],np.cumprod(1+pr.values)])

def sim(v, s, H, rule, buy=0.0012, base=1000.0):
    """rule: ('flat',) ('grow',g年增长) ('dip',k) 相对近12月高点每跌10%多投k倍 ('val',) """
    units=0.0; cf=[]; peak=v[s]
    for t in range(H):
        i=s+t; p=v[i]; peak=max(peak, max(v[max(s,i-11):i+1]))
        amt=base
        if rule[0]=="grow": amt=base*(1+rule[1])**(t/12.0)
        elif rule[0]=="dip":
            dd=p/peak-1
            amt=base*(1+rule[1]*max(0,-dd)/0.10)
        units+=amt*(1-buy)/p; cf.append(amt)
    return E.xirr_monthly(cf, units*v[s+H]), sum(cf), units*v[s+H]

print("【1】递增定投（每年提高投入额）vs 定额 —— 滚动10年，全部起点")
print(f"{'策略':<22}{'中位IRR':>10}{'10%分位':>10}{'最差':>10}{'中位投入':>11}{'中位终值':>11}")
H=120
for rule,lab in [(("flat",),"定额 1000/月"),(("grow",0.05),"每年+5%"),(("grow",0.10),"每年+10%"),(("grow",0.15),"每年+15%")]:
    res=[]
    for s in range(0,len(v_all)-H-1):
        irr,c,f=sim(v_all,s,H,rule)
        if irr==irr: res.append((irr,c,f))
    r=np.array(res)
    print(f"{lab:<22}{np.median(r[:,0])*100:9.2f}%{np.percentile(r[:,0],10)*100:9.2f}%{r[:,0].min()*100:9.2f}%"
          f"{np.median(r[:,1]):10,.0f}{np.median(r[:,2]):10,.0f}")
print("  注：IRR 已按现金流时点加权，递增定投的 IRR 变化反映的是'择时效应'而非'投得多'")

print("\n【2】逆势加码（相对近12月高点每跌10%，多投k倍）")
print(f"{'策略':<22}{'中位IRR':>10}{'10%分位':>10}{'最差':>10}{'中位投入':>11}")
for rule,lab in [(("flat",),"不加码"),(("dip",0.5),"跌10%多投50%"),(("dip",1.0),"跌10%翻倍"),(("dip",2.0),"跌10%投3倍")]:
    res=[]
    for s in range(0,len(v_all)-H-1):
        irr,c,f=sim(v_all,s,H,rule)
        if irr==irr: res.append((irr,c,f))
    r=np.array(res)
    print(f"{lab:<22}{np.median(r[:,0])*100:9.2f}%{np.percentile(r[:,0],10)*100:9.2f}%{r[:,0].min()*100:9.2f}%{np.median(r[:,1]):10,.0f}")

print("\n【3】同样规则用在全仓沪深300上（波动更大，加码效果应更明显）")
RH=A["A股沪深300"].dropna().pct_change().dropna()-0.002/12
vh=np.concatenate([[1.0],np.cumprod(1+RH.values)])
for rule,lab in [(("flat",),"不加码"),(("dip",1.0),"跌10%翻倍"),(("dip",2.0),"跌10%投3倍")]:
    res=[]
    for s in range(0,len(vh)-H-1):
        irr,c,f=sim(vh,s,H,rule)
        if irr==irr: res.append((irr,c,f))
    r=np.array(res)
    print(f"  {lab:<20}{np.median(r[:,0])*100:9.2f}%{np.percentile(r[:,0],10)*100:9.2f}%{r[:,0].min()*100:9.2f}%{np.median(r[:,1]):10,.0f}")

print("\n【4】再平衡阈值（偏离目标多少才动手）—— 滚动10年")
def rb_sim(s,H,thr,mode):
    Rm=R.values; units=np.zeros(len(AS)); cf=[]
    for t in range(H):
        i=s+t; net=1000*0.9988
        tot=units.sum()
        if tot>0 and mode=="cash":
            tgt=(tot+net)*PLAN; gap=np.maximum(tgt-units,0)
            alloc=gap/gap.sum()*net if gap.sum()>1e-9 else net*PLAN
        else: alloc=net*PLAN
        units=units+alloc
        units=units*(1+Rm[i])
        if thr is not None and units.sum()>0:
            wnow=units/units.sum()
            if np.abs(wnow-PLAN).max()>thr: units=units.sum()*PLAN
        cf.append(1000)
    return E.xirr_monthly(cf, units.sum())
print(f"{'规则':<26}{'中位IRR':>10}{'10%分位':>10}{'最差':>10}")
for thr,mode,lab in [(None,"none","纯定额买入，不管权重"),(None,"cash","新钱补低配(不卖出)"),
                     (0.10,"cash","新钱+偏离10pp才卖出"),(0.05,"cash","新钱+偏离5pp才卖出"),
                     (0.03,"cash","新钱+偏离3pp就卖出")]:
    res=[rb_sim(s,H,thr,mode) for s in range(0,len(R)-H-1,2)]
    r=np.array([x for x in res if x==x])
    print(f"{lab:<26}{np.median(r)*100:9.2f}%{np.percentile(r,10)*100:9.2f}%{r.min()*100:9.2f}%")
