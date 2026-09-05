# -*- coding: utf-8 -*-
"""主口径：2008-01~2026-09 含黄金全资产长窗口（18.7年）。附 2005 起无黄金窗口做更长期验证。"""
import sys, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
PLAN={"A股红利":.24,"A股中证500":.06,"港股红利":.10,"美股标普500":.18,"美股纳指100":.14,"黄金":.13,"债券":.15}

A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
G=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
A["黄金AU0"]=G
COL={"A股红利":"A股红利","A股中证500":"A股中证500","港股红利":"港股红利TR",
     "美股标普500":"美股标普500(人民币)","美股纳指100":"美股纳斯达克(人民币)","黄金":"黄金AU0","债券":"债券中证全债"}
# 模拟基金年费（黄金用交叉验证得到的 0.30% 跟踪差）
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}
cols=[COL[k] for k in PLAN]; w=np.array([PLAN[k] for k in PLAN])
M=A[cols+["A股沪深300"]].dropna()
print(f"主窗口 {M.index.min().date()} ~ {M.index.max().date()}  {len(M)}月 ({len(M)/12:.1f}年)  资产{len(cols)}类（含黄金）")
R=M[cols].pct_change().dropna()-np.array([FEE[c] for c in cols])/12.0
px=pd.DataFrame({"P":(1+(R*w).sum(axis=1)).cumprod()})
hs=pd.DataFrame({"P":(1+(M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12)).cumprod()})

print("\n各资产在本窗口的表现:")
for c in cols:
    s=M[c]; r=s.pct_change().dropna()-FEE[c]/12; yy=len(r)/12
    cum=(1+r).cumprod(); dd=(cum/cum.cummax()-1).min()
    print(f"  {c:22s} CAGR={((1+r).prod()**(1/yy)-1)*100:6.2f}%  波动={r.std()*np.sqrt(12)*100:5.1f}%  最大回撤={dd*100:6.1f}%")

def roll(p,H):
    rd=E.rolling_dca(p,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    return dict(n=len(i),med=i.median(),p10=i.quantile(.1),p90=i.quantile(.9),mn=i.min(),
                loss=float((i<0).mean()),dd=rd["maxdd"].median()), rd

print("\n"+"="*100); print("【主口径 · 含黄金 · 18.7年】")
print(f"{'期限':<6}{'方案':<14}{'中位IRR':>9}{'10%分位':>9}{'90%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'样本':>6}")
tab={}
for H,tag in [(36,"3年"),(60,"5年"),(120,"10年"),(180,"15年")]:
    a,_=roll(px,H); b,_=roll(hs,H); tab[tag]={"port":a,"hs":b}
    for nm,s in [("本方案",a),("全仓沪深300",b)]:
        print(f"{tag:<6}{nm:<14}{s['med']*100:>8.2f}%{s['p10']*100:>8.2f}%{s['p90']*100:>8.2f}%"
              f"{s['mn']*100:>8.2f}%{s['loss']*100:>7.1f}%{s['dd']*100:>8.1f}%{s['n']:>6}")

Hf,irrf=E.dca_path(px,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
Hh,irrh=E.dca_path(hs,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
print(f"\n全程 {len(M)/12:.1f} 年定投：本方案 IRR={irrf*100:.2f}% 终值={Hf['value'].iloc[-1]:,.0f}"
      f" | 沪深300 IRR={irrh*100:.2f}% 终值={Hh['value'].iloc[-1]:,.0f} | 累计投入={Hf['cost'].iloc[-1]:,.0f}")

# 黄金边际贡献（同窗口对比）
w_ng=np.array([PLAN[k] for k in PLAN]); i_g=list(PLAN).index("黄金")
w2=w_ng.copy(); w2[i_g]=0; w2=w2/w2.sum()
px2=pd.DataFrame({"P":(1+(R*w2).sum(axis=1)).cumprod()})
a2,_=roll(px2,120); a1,_=roll(px,120)
print(f"\n黄金边际贡献(10年定投): 含黄金 中位{a1['med']*100:.2f}% 最差{a1['mn']*100:.2f}% 浮亏{a1['dd']*100:.1f}%"
      f" | 无黄金 中位{a2['med']*100:.2f}% 最差{a2['mn']*100:.2f}% 浮亏{a2['dd']*100:.1f}%")

viz={"dca":{"d":[d.strftime("%Y-%m") for d in Hf.index],
            "cost":[round(float(x)) for x in Hf["cost"]],
            "port":[round(float(x)) for x in Hf["value"]],
            "hs300":[round(float(x)) for x in Hh["value"]],
            "irr":round(float(irrf),4),"irr_hs":round(float(irrh),4)},"roll":{}}
for H,tag in [(60,"5y"),(120,"10y"),(180,"15y")]:
    _,ra=roll(px,H); _,rb=roll(hs,H)
    viz["roll"][tag]={"d":[d.strftime("%Y-%m") for d in ra["start"]],
        "p":[round(float(x),4) for x in ra["irr"]],"h":[round(float(x),4) for x in rb["irr"]]}
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
CB=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
corr=B[CB].dropna().pct_change().corr()
viz["corr"]={"labels":CB,"m":[[round(float(corr.iloc[i,j]),2) for j in range(len(CB))] for i in range(len(CB))]}
json.dump(viz,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
json.dump({k:{kk:{k3:round(float(v3),5) for k3,v3 in vv.items()} for kk,vv in v.items()} for k,v in tab.items()},
          open(f"{ROOT}/out/numbers.json","w"),ensure_ascii=False,indent=1)
print("\n已导出 viz.json / numbers.json")
