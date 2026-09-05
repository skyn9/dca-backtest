# -*- coding: utf-8 -*-
"""导出报告所需的全部数据为 JSON"""
import sys, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
FEE={"A股沪深300":.0020,"A股中证500":.0020,"A股红利":.0020,"债券中证全债":.0030,
     "美股标普500(人民币)":.0065,"美股纳斯达克(人民币)":.0065,"港股红利TR":.0060}
L=["A股红利","A股沪深300","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
R=A[L].pct_change().dropna()-np.array([FEE[c] for c in L])/12.0
W=np.array([.25,.00,.05,.10,.18,.14,.28]); W=W/W.sum()   # 长窗口版(黄金13%按比例并入债券)
pr=(R*W).sum(axis=1)
out={}
# 1) 组合 vs 基准 净值曲线(归一)
cur={"本方案":(1+pr).cumprod(),
     "沪深300":(1+R["A股沪深300"]).cumprod(),
     "中证红利":(1+R["A股红利"]).cumprod(),
     "标普500(人民币)":(1+R["美股标普500(人民币)"]).cumprod(),
     "纳指(人民币)":(1+R["美股纳斯达克(人民币)"]).cumprod()}
cv=pd.DataFrame(cur); cv=cv/cv.iloc[0]
out["curve"]={"dates":[d.strftime("%Y-%m") for d in cv.index],
              "series":{k:[round(float(x),4) for x in cv[k]] for k in cv.columns}}
# 2) 定投累计投入 vs 市值（全程21.7年）
px=pd.DataFrame({"P":(1+pr).cumprod()})
H,irr=E.dca_path(px,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
out["dca_full"]={"dates":[d.strftime("%Y-%m") for d in H.index],
                 "cost":[round(float(x)) for x in H["cost"]],
                 "value":[round(float(x)) for x in H["value"]],"irr":round(float(irr),4)}
Hb,irrb=E.dca_path(pd.DataFrame({"P":(1+R["A股沪深300"]).cumprod()}),pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
out["dca_hs300"]={"value":[round(float(x)) for x in Hb["value"]],"irr":round(float(irrb),4)}
# 3) 滚动IRR分布(5/10/15年) 本方案 vs 沪深300
def roll(series,H_):
    p=pd.DataFrame({"P":series})
    rd=E.rolling_dca(p,pd.Series({"P":1.0}),H_,annual_fee=None,buy_fee=0.0012)
    return rd
out["roll"]={}
for H_,tag in [(60,"5y"),(120,"10y"),(180,"15y")]:
    a=roll((1+pr).cumprod(),H_); b=roll((1+R["A股沪深300"]).cumprod(),H_)
    out["roll"][tag]={"dates":[d.strftime("%Y-%m") for d in a["start"]],
        "port":[round(float(x),4) for x in a["irr"]],
        "hs300":[round(float(x),4) for x in b["irr"]],
        "stat":{"port":{k:round(float(v),4) for k,v in
                 dict(med=a["irr"].median(),p10=a["irr"].quantile(.1),mn=a["irr"].min(),loss=(a["irr"]<0).mean()).items()},
                "hs300":{k:round(float(v),4) for k,v in
                 dict(med=b["irr"].median(),p10=b["irr"].quantile(.1),mn=b["irr"].min(),loss=(b["irr"]<0).mean()).items()}}}
# 4) 资产长期表现
perf=E.perf_stats(A[L],FEE)
out["assets"]=[{k:(round(float(v),4) if isinstance(v,(int,float,np.floating)) else str(v)) for k,v in r.items()} for _,r in perf.iterrows()]
# 5) 相关性
CB=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
corr=B[CB].dropna().pct_change().corr()
out["corr"]={"labels":CB,"m":[[round(float(corr.iloc[i,j]),2) for j in range(len(CB))] for i in range(len(CB))]}
json.dump(out,open(f"{ROOT}/out/report_data.json","w"),ensure_ascii=False)
print("导出完成")
print("全程定投21.7年 IRR=",round(irr*100,2),"% 投入",H['cost'].iloc[-1],"终值",round(H['value'].iloc[-1]))
print("沪深300同期    IRR=",round(irrb*100,2),"% 终值",round(Hb['value'].iloc[-1]))
for t in ["5y","10y","15y"]:
    s=out["roll"][t]["stat"]; print(t,"本方案 中位",s["port"]["med"],"最差",s["port"]["mn"],"亏损率",s["port"]["loss"],
                                    "| 沪深300 中位",s["hs300"]["med"],"最差",s["hs300"]["mn"],"亏损率",s["hs300"]["loss"])
