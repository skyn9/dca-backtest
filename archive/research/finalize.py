# -*- coding: utf-8 -*-
"""统一权重口径，重算报告所需的全部数字 + 图表数据。"""
import sys, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"

# ===== 唯一权重定义（方案表）=====
PLAN = {"A股红利":.24,"A股中证500":.06,"港股红利":.10,"美股标普500":.18,
        "美股纳指100":.14,"黄金":.13,"债券":.15}
assert abs(sum(PLAN.values())-1)<1e-9, sum(PLAN.values())
print("方案权重:", PLAN, " 合计", sum(PLAN.values()))

# ---- 长窗口(21.7y, 无黄金)：黄金13%剔除后其余等比放大 ----
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
MAPL={"A股红利":"A股红利","A股中证500":"A股中证500","港股红利":"港股红利TR",
      "美股标普500":"美股标普500(人民币)","美股纳指100":"美股纳斯达克(人民币)","债券":"债券中证全债"}
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,
     "美股标普500(人民币)":.0065,"美股纳斯达克(人民币)":.0065,"债券中证全债":.0030,"A股沪深300":.0020}
colL=[MAPL[k] for k in MAPL]; wL=np.array([PLAN[k] for k in MAPL]); wL=wL/wL.sum()
print("\n长窗口(剔黄金后等比放大):", {c:f"{w*100:.1f}%" for c,w in zip(colL,wL)})
RL=A[colL].pct_change().dropna()-np.array([FEE[c] for c in colL])/12.0
prL=(RL*wL).sum(axis=1); pxL=pd.DataFrame({"P":(1+prL).cumprod()})
hsL=pd.DataFrame({"P":(1+(A["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12)).cumprod()})

# ---- 实盘窗口(13.1y, 含黄金；港股用恒生=保守) ----
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
MAPB={"A股红利":"A股红利","A股中证500":"A股中证500","港股红利":"港股恒生",
      "美股标普500":"美股标普500","美股纳指100":"美股纳指100","黄金":"黄金","债券":"债券"}
colB=[MAPB[k] for k in MAPB]; wB=np.array([PLAN[k] for k in MAPB])
RB=B[colB].dropna().pct_change().dropna()
prB=(RB*wB).sum(axis=1); pxB=pd.DataFrame({"P":(1+prB).cumprod()})
hsB=pd.DataFrame({"P":(1+B["A股沪深300"].dropna().reindex(RB.index).fillna(0)).cumprod()})
hsB=pd.DataFrame({"P":(1+B["A股沪深300"].pct_change().dropna().reindex(RB.index)).cumprod()})

def roll(px,H):
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    return dict(n=len(i),med=i.median(),p10=i.quantile(.10),p90=i.quantile(.90),mn=i.min(),mx=i.max(),
                loss=float((i<0).mean()),dd=rd["maxdd"].median(),wdd=rd["maxdd"].min()), rd

out={}
print("\n"+"="*104); print("【长窗口 2005-01~2026-09（21.7年，指数全收益，不含黄金）】")
print(f"{'期限':<6}{'方案':<14}{'中位IRR':>9}{'10%分位':>9}{'90%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'样本':>6}")
tab={}
for H,tag in [(60,"5年"),(120,"10年"),(180,"15年")]:
    a,_=roll(pxL,H); b,_=roll(hsL,H); tab[tag]={"port":a,"hs":b}
    for nm,s in [("本方案",a),("全仓沪深300",b)]:
        print(f"{tag:<6}{nm:<14}{s['med']*100:>8.2f}%{s['p10']*100:>8.2f}%{s['p90']*100:>8.2f}%"
              f"{s['mn']*100:>8.2f}%{s['loss']*100:>7.1f}%{s['dd']*100:>8.1f}%{s['n']:>6}")
out["tab_long"]={k:{kk:{k3:round(float(v3),5) for k3,v3 in vv.items()} for kk,vv in v.items()} for k,v in tab.items()}

print("\n"+"="*104); print(f"【实盘窗口 {RB.index.min().date()}~{RB.index.max().date()}（{len(RB)/12:.1f}年，真实净值，含黄金）】")
print(f"{'期限':<6}{'方案':<14}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'样本':>6}")
tab2={}
for H,tag in [(36,"3年"),(60,"5年"),(120,"10年")]:
    a,_=roll(pxB,H); b,_=roll(hsB,H); tab2[tag]={"port":a,"hs":b}
    for nm,s in [("本方案",a),("全仓沪深300",b)]:
        print(f"{tag:<6}{nm:<14}{s['med']*100:>8.2f}%{s['p10']*100:>8.2f}%{s['mn']*100:>8.2f}%"
              f"{s['loss']*100:>7.1f}%{s['dd']*100:>8.1f}%{s['n']:>6}")
out["tab_fund"]={k:{kk:{k3:round(float(v3),5) for k3,v3 in vv.items()} for kk,vv in v.items()} for k,v in tab2.items()}

# ---- 全程定投轨迹（长窗口）----
Hf,irrf=E.dca_path(pxL,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
Hh,irrh=E.dca_path(hsL,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
print(f"\n全程 21.7 年：本方案 IRR={irrf*100:.2f}% 终值={Hf['value'].iloc[-1]:,.0f} | "
      f"沪深300 IRR={irrh*100:.2f}% 终值={Hh['value'].iloc[-1]:,.0f} | 投入={Hf['cost'].iloc[-1]:,.0f}")

# ---- 导出图表数据 ----
viz={}
viz["dca"]={"d":[d.strftime("%Y-%m") for d in Hf.index],
            "cost":[round(float(x)) for x in Hf["cost"]],
            "port":[round(float(x)) for x in Hf["value"]],
            "hs300":[round(float(x)) for x in Hh["value"]],
            "irr":round(float(irrf),4),"irr_hs":round(float(irrh),4)}
viz["roll"]={}
for H,tag in [(60,"5y"),(120,"10y"),(180,"15y")]:
    _,ra=roll(pxL,H); _,rb=roll(hsL,H)
    viz["roll"][tag]={"d":[d.strftime("%Y-%m") for d in ra["start"]],
        "p":[round(float(x),4) for x in ra["irr"]],
        "h":[round(float(x),4) for x in rb["irr"]]}
CB=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
corr=B[CB].dropna().pct_change().corr()
viz["corr"]={"labels":CB,"m":[[round(float(corr.iloc[i,j]),2) for j in range(len(CB))] for i in range(len(CB))]}
json.dump(viz,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
json.dump(out,open(f"{ROOT}/out/numbers.json","w"),ensure_ascii=False,indent=1)
import os; print("viz.json",os.path.getsize(f"{ROOT}/out/viz.json"),"字节")
