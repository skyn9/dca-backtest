# -*- coding: utf-8 -*-
"""最终报告数据：2008起含黄金主窗口 + 起点敏感性"""
import sys, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
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
viz={}

def build(st, gold=True):
    use=[c for c in cols if gold or c!="黄金AU0"]
    ww=np.array([PLAN[k] for k in PLAN if gold or COL[k]!="黄金AU0"]); ww=ww/ww.sum()
    M=A[use+["A股沪深300"]].dropna(); M=M[M.index>=st]
    R=M[use].pct_change().dropna()-np.array([FEE[c] for c in use])/12.0
    px=pd.DataFrame({"P":(1+(R*ww).sum(axis=1)).cumprod()})
    hs=pd.DataFrame({"P":(1+(M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12)).cumprod()})
    return M,px,hs

M,px,hs=build("2008-01")
Hf,irrf=E.dca_path(px,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
Hh,irrh=E.dca_path(hs,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
viz["dca"]={"d":[d.strftime("%Y-%m") for d in Hf.index],
  "cost":[round(float(x)) for x in Hf["cost"]],"port":[round(float(x)) for x in Hf["value"]],
  "hs300":[round(float(x)) for x in Hh["value"]],"irr":round(float(irrf),4),"irr_hs":round(float(irrh),4)}
print(f"主窗口 {M.index.min().date()}~{M.index.max().date()} {len(M)}月 | 本方案IRR={irrf*100:.2f}% 终值={Hf['value'].iloc[-1]:,.0f} | 沪深300 {irrh*100:.2f}% {Hh['value'].iloc[-1]:,.0f} | 投入{Hf['cost'].iloc[-1]:,.0f}")

viz["roll"]={}; viz["stat"]={}
for H,tag in [(60,"5y"),(120,"10y"),(180,"15y")]:
    ra=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    rb=E.rolling_dca(hs,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    viz["roll"][tag]={"d":[d.strftime("%Y-%m") for d in ra["start"]],
        "p":[round(float(x),4) for x in ra["irr"]],"h":[round(float(x),4) for x in rb["irr"]]}
    f=lambda rd:{k:round(float(v),4) for k,v in dict(n=len(rd["irr"].dropna()),med=rd["irr"].median(),
        p10=rd["irr"].quantile(.1),p90=rd["irr"].quantile(.9),mn=rd["irr"].min(),
        loss=(rd["irr"]<0).mean(),dd=rd["maxdd"].median()).items()}
    viz["stat"][tag]={"port":f(ra),"hs":f(rb)}
    print(f"  {tag}: 本方案 med={ra['irr'].median()*100:.2f}% mn={ra['irr'].min()*100:.2f}% loss={(ra['irr']<0).mean()*100:.1f}%"
          f" | 300 med={rb['irr'].median()*100:.2f}% mn={rb['irr'].min()*100:.2f}% loss={(rb['irr']<0).mean()*100:.1f}%")

# 起点敏感性
WIN=[("2005-01","21.7年",False),("2008-01","18.7年",True),("2011-01","15.7年",True),("2013-09","13.1年",True)]
viz["windows"]=[]
for st,lab,g in WIN:
    _,p2,h2=build(st,g)
    row={"start":st,"span":lab,"gold":g}
    for H,tag in [(60,"5y"),(120,"10y")]:
        ra=E.rolling_dca(p2,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
        rb=E.rolling_dca(h2,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
        row[tag]={"pm":round(float(ra["irr"].median()),4),"pn":round(float(ra["irr"].min()),4),
                  "pl":round(float((ra["irr"]<0).mean()),4),"hm":round(float(rb["irr"].median()),4),
                  "hn":round(float(rb["irr"].min()),4),"hl":round(float((rb["irr"]<0).mean()),4)}
    viz["windows"].append(row)
    print(f"  窗口{st}: 5y本方案{row['5y']['pm']*100:.2f}%/亏{row['5y']['pl']*100:.0f}%  10y {row['10y']['pm']*100:.2f}%/最差{row['10y']['pn']*100:.2f}%")

# 各资产不同起点 CAGR
viz["startdep"]={"starts":["2005-01","2008-01","2011-01","2015-06"],"rows":[]}
for c,nm in [("A股红利","A股红利"),("A股中证500","A股中证500"),("A股沪深300","A股沪深300"),
             ("港股红利TR","港股红利"),("美股标普500(人民币)","美股标普500"),
             ("美股纳斯达克(人民币)","美股纳指100"),("黄金AU0","黄金"),("债券中证全债","债券")]:
    vals=[]
    for st in viz["startdep"]["starts"]:
        s=A[c].dropna(); s=s[s.index>=st]
        vals.append(round(float((s.iloc[-1]/s.iloc[0])**(12/(len(s)-1))-1),4) if len(s)>24 else None)
    viz["startdep"]["rows"].append({"name":nm,"v":vals})
    print(f"  {nm:12s} " + " ".join(f"{x*100:6.2f}%" if x else "   —  " for x in vals))

B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
CB=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
corr=B[CB].dropna().pct_change().corr()
viz["corr"]={"labels":CB,"m":[[round(float(corr.iloc[i,j]),2) for j in range(len(CB))] for i in range(len(CB))]}
json.dump(viz,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
import os; print("\nviz.json",os.path.getsize(f"{ROOT}/out/viz.json"),"字节")

# ==== 追加：统一口径的起点敏感性（各资产 vs 组合，均为"滚动10年定投IRR中位数"）====
print("\n【统一口径：各起点窗口下的 滚动10年定投IRR 中位数】")
starts=[("2005-01","2005起"),("2008-01","2008起"),("2011-01","2011起"),("2013-09","2013起")]
sens={"starts":[s[1] for s in starts],"rows":[]}
ASSETS=[("A股红利","A股红利"),("A股中证500","中证500"),("A股沪深300","沪深300"),("港股红利TR","港股红利"),
        ("美股标普500(人民币)","标普500"),("美股纳斯达克(人民币)","纳指100"),("黄金AU0","黄金"),("债券中证全债","债券")]
for c,nm in ASSETS:
    vals=[]
    for st,_ in starts:
        s=A[c].dropna(); s=s[s.index>=st]
        r=s.pct_change().dropna()-FEE[c]/12
        p=pd.DataFrame({"P":(1+r).cumprod()})
        if len(p)<132: vals.append(None); continue
        rd=E.rolling_dca(p,pd.Series({"P":1.0}),120,annual_fee=None,buy_fee=0.0012)
        vals.append(round(float(rd["irr"].median()),4))
    sens["rows"].append({"name":nm,"v":vals,"kind":"asset"})
    print(f"  {nm:10s} " + " ".join(f"{x*100:7.2f}%" if x is not None else "    —  " for x in vals))
# 组合
vals=[]
for st,_ in starts:
    g = st!="2005-01"
    _,p2,_=build(st,g)
    rd=E.rolling_dca(p2,pd.Series({"P":1.0}),120,annual_fee=None,buy_fee=0.0012)
    vals.append(round(float(rd["irr"].median()),4))
sens["rows"].append({"name":"★本方案","v":vals,"kind":"port"})
print(f"  {'★本方案':10s} " + " ".join(f"{x*100:7.2f}%" for x in vals))
for r in sens["rows"]:
    vv=[x for x in r["v"] if x is not None]
    r["lo"],r["hi"],r["rng"]=min(vv),max(vv),round(max(vv)-min(vv),4)
    print(f"    {r['name']:10s} 区间 {r['lo']*100:6.2f}% ~ {r['hi']*100:6.2f}%  极差 {r['rng']*100:5.2f}pp")
viz["sens"]=sens
json.dump(viz,open(f"{ROOT}/out/viz.json","w"),ensure_ascii=False,separators=(",",":"))
print("\nviz.json", os.path.getsize(f"{ROOT}/out/viz.json"),"字节")
