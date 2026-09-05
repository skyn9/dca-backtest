# -*- coding: utf-8 -*-
"""验证港股红利的股息假设：多指数交叉 + 真实基金比对"""
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch
ROOT="/Users/sky/PycharmProjects/DCA"

print("【1】港股红利系指数横向比较（同一重叠期）")
IDX={}
for c in ["930838","H30093","H30533"]:
    try: IDX[c]=fetch.csindex(c).set_index("date")["px"]
    except Exception as e: print("  fail",c,str(e)[:40])
df=pd.DataFrame(IDX).dropna()
print(f"  重叠期 {df.index.min().date()} ~ {df.index.max().date()}  {len(df)}个交易日")
yy=(df.index.max()-df.index.min()).days/365.25
for c in df.columns:
    print(f"    {c}: CAGR={((df[c].iloc[-1]/df[c].iloc[0])**(1/yy)-1)*100:6.2f}%")
if "930838" in df and "H30533" in df:
    d=((df['H30533'].iloc[-1]/df['H30533'].iloc[0])**(1/yy)-1)-((df['930838'].iloc[-1]/df['930838'].iloc[0])**(1/yy)-1)
    print(f"  H30533(全收益) - 930838 = {d*100:+.2f}pp/年")
if "930838" in df and "H30093" in df:
    d=((df['H30093'].iloc[-1]/df['H30093'].iloc[0])**(1/yy)-1)-((df['930838'].iloc[-1]/df['930838'].iloc[0])**(1/yy)-1)
    print(f"  H30093        - 930838 = {d*100:+.2f}pp/年")

print("\n【2】用真实港股红利基金净值反推（基金净值天然含分红再投资）")
FUNDS=[("018387","华泰柏瑞港股通红利ETF联接A"),("014519","博时恒生高股息率ETF联接A"),
       ("019260","富国恒生红利ETF联接A"),("021457","易方达恒生红利低波ETF联接A"),
       ("004532","民生加银港股通高股息A")]
g=pd.DataFrame(IDX).ffill()
for code,nm in FUNDS:
    try:
        f,_=fetch.fund_hist(code)
        fm=f.set_index("date")["adj"]
        j=pd.concat([fm.rename("fund"), g["930838"].rename("idx")],axis=1).dropna()
        if len(j)<250: print(f"  {code} {nm[:20]:22s} 数据不足({len(j)}日)"); continue
        yy2=(j.index.max()-j.index.min()).days/365.25
        cf=(j["fund"].iloc[-1]/j["fund"].iloc[0])**(1/yy2)-1
        ci=(j["idx"].iloc[-1]/j["idx"].iloc[0])**(1/yy2)-1
        print(f"  {code} {nm[:20]:22s} {yy2:4.1f}y  基金{cf*100:6.2f}%  指数(价格){ci*100:6.2f}%  差={(cf-ci)*100:+5.2f}pp/年")
    except Exception as e: print(f"  {code} {nm}: {str(e)[:50]}")
print("\n  注：基金差额 = 股息再投资 - 管理费(0.2~0.6%) - 跟踪误差 - 港股通红利税(20%)")
print("      故 差额 + 费率 ≈ 税后净股息贡献")
