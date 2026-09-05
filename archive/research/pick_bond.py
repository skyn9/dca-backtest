# -*- coding: utf-8 -*-
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
allf=pd.read_csv(f"{ROOT}/data/all_funds.csv",dtype={"基金代码":str})
allf["name"]=allf["基金简称"]; allf["code"]=allf["基金代码"]
# 政金债/国开债/中债指数型纯债（低费率、低波动、与股票低相关）
m=allf[allf["name"].str.contains(r"政金债|国开(行|债)|中债.*(国开|政策性|综合|总财富)|(3-5年|1-3年|7-10年).*(国开|政金|国债)",regex=True,na=False)]
m=m[m["基金类型"].str.contains("指数型-固收|债券型",na=False)]
m=m[~m["name"].str.contains(r"[CEIDY]$|C类|后端",regex=True,na=False)]
m=m.drop_duplicates("code")
print(f"政金债/国开债指数基金候选 {len(m)} 只，抓前16只费率/规模\n")
print(f"{'代码':<8}{'名称':<34}{'年费率':>7}{'申购':>7}{'规模亿':>8}{'成立':>6}{'年化':>8}{'最大回撤':>9}")
rows=[]
for _,r in m.head(16).iterrows():
    try:
        fee=fetch.fund_fees(r["code"]); df,meta=fetch.fund_hist(r["code"])
        yrs=(df["date"].max()-df["date"].min()).days/365.25
        if yrs<1: continue
        cagr=(df["adj"].iloc[-1]/df["adj"].iloc[0])**(1/yrs)-1
        cum=df["adj"]; mdd=(cum/cum.cummax()-1).min()
        sc=meta.get("scale_series") or []; s=sc[-1][1]["y"] if sc else None
        rows.append((r["code"],r["name"],fee["total_annual"],fee["buy_disc"],s,yrs,cagr,mdd))
        print(f"{r['code']:<8}{str(r['name'])[:32]:<34}{fee['total_annual']:>6.2f}%{str(fee['buy_disc']):>6}%{str(s):>7} {yrs:>5.1f}y{cagr*100:>7.2f}%{mdd*100:>8.2f}%")
    except Exception as e: print(f"{r['code']} skip {str(e)[:40]}")
