# -*- coding: utf-8 -*-
"""稳健性三重检验：①子样本(A股牛市期 vs 美股牛市期) ②收益率压力情景 ③黄金边际贡献"""
import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
FEE={"A股沪深300":0.0020,"A股中证500":0.0020,"A股红利":0.0020,"A股上证50":0.0020,
     "A股中证1000":0.0020,"债券中证全债":0.0030,"美股标普500(人民币)":0.0065,"美股纳斯达克(人民币)":0.0065}
ASSETS=["A股红利","A股沪深300","A股中证500","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
R_full=A[ASSETS].pct_change().dropna()-np.array([FEE[c] for c in ASSETS])/12.0

CANDS={
 "优化解(Top60均值)": [.251,.068,.065,.165,.260,.191],
 "全仓沪深300":       [0,1,0,0,0,0],
 "全仓A股红利":        [1,0,0,0,0,0],
 "沪深300+债60/40":  [0,.6,0,0,0,.4],
 "等权6资产":         [1/6]*6,
 "简化均衡(红利30美股40债30)":[.30,0,0,.20,.20,.30],
}
def ev(R, w, H):
    pr=(R*np.array(w)).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    if len(i)==0: return None
    return dict(n=len(i),med=i.median(),p10=i.quantile(.10),mn=i.min(),loss=(i<0).mean())

print("="*112); print("【检验① 子样本】看权重是否只在某个时代有效")
SUB=[("2005-01~2015-12 (A股两轮牛市/美股金融危机)","2005-01-01","2015-12-31",60),
     ("2016-01~2026-09 (A股长熊/美股大牛)","2016-01-01","2026-09-30",60),
     ("全样本 2005-2026",None,None,120)]
for tag,s,e,H in SUB:
    Rs=R_full.loc[s:e] if s else R_full
    print(f"\n--- {tag}  滚动{H//12}年定投  月数={len(Rs)} ---")
    print(f"{'组合':<28}{'样本':>5}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}")
    for nm,w in CANDS.items():
        r=ev(Rs,w,H)
        if r: print(f"{nm:<28}{r['n']:>5}{r['med']*100:>8.2f}%{r['p10']*100:>8.2f}%{r['mn']*100:>8.2f}%{r['loss']*100:>7.1f}%")

print("\n"+"="*112); print("【检验② 压力情景】把各资产未来收益强行下调到保守假设，重跑（检验权重是否依赖高收益预期）")
# 情景: 对月度收益序列做均值平移，保留波动与相关结构
SCEN={"基准(历史原样)":None,
      "温和降温: 美股-3%/A股-1%":{"美股标普500(人民币)":-.03,"美股纳斯达克(人民币)":-.03,"A股红利":-.01,"A股沪深300":-.01,"A股中证500":-.01},
      "美股大幅降温 -6%":{"美股标普500(人民币)":-.06,"美股纳斯达克(人民币)":-.06},
      "美股-6% & 债券-1.5%(低利率)":{"美股标普500(人民币)":-.06,"美股纳斯达克(人民币)":-.06,"债券中证全债":-.015},
      "A股复苏+美股降温":{"美股标普500(人民币)":-.06,"美股纳斯达克(人民币)":-.06,"A股红利":+.02,"A股沪深300":+.03,"A股中证500":+.03}}
for sc,adj in SCEN.items():
    R=R_full.copy()
    if adj:
        for k,v in adj.items(): R[k]=R[k]+v/12.0
    print(f"\n--- 情景: {sc} ---")
    print(f"{'组合':<28}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}")
    for nm,w in CANDS.items():
        r=ev(R,w,120)
        if r: print(f"{nm:<28}{r['med']*100:>8.2f}%{r['p10']*100:>8.2f}%{r['mn']*100:>8.2f}%")
