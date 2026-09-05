# -*- coding: utf-8 -*-
"""最终定稿：实盘窗口(含黄金,真实净值)确定权重"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
L=["A股红利","A股沪深300","A股中证500","港股恒生","美股标普500","美股纳指100","黄金","债券"]
R=B[L].dropna().pct_change().dropna()
C={
 "①6只·均衡(主推)":      [.24,.00,.06,.10,.18,.14,.13,.15],
 "②5只·去港股":         [.26,.00,.06,.00,.20,.15,.13,.20],
 "③4只·极简":          [.30,.00,.00,.00,.25,.00,.15,.30],
 "④4只·极简含纳指":       [.28,.00,.00,.00,.17,.15,.15,.25],
 "⑤7只·全配":          [.22,.08,.05,.10,.18,.15,.12,.10],
 "⑥进取型(债10金10)":    [.25,.00,.08,.10,.20,.17,.10,.10],
 "⑦保守型(债30金15)":    [.20,.00,.03,.07,.14,.11,.15,.30],
 "—基准:全仓沪深300":     [0,1,0,0,0,0,0,0],
}
def ev(w,H):
    w=np.array(w,dtype=float); w=w/w.sum()
    pr=(R*w).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    ann=(1+pr).prod()**(12/len(pr))-1; vol=pr.std()*np.sqrt(12)
    cum=(1+pr).cumprod(); mdd=(cum/cum.cummax()-1).min()
    return i.median(),i.quantile(.1),i.min(),(i<0).mean(),rd["maxdd"].median(),ann,vol,mdd
for H,hn in [(36,"3年"),(60,"5年"),(120,"10年")]:
    print(f"\n=== 定投{hn} (实盘窗口 2013-09~2026-09, 13.1年, 真实净值含黄金) ===")
    print(f"{'方案':<22}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}{'组合年化':>9}{'波动':>7}{'最大回撤':>9}")
    for nm,w in C.items():
        m,p,mn,lp,dd,ann,vol,mdd=ev(w,H)
        print(f"{nm:<22}{m*100:>8.2f}%{p*100:>8.2f}%{mn*100:>8.2f}%{lp*100:>7.1f}%{dd*100:>8.1f}%{ann*100:>8.2f}%{vol*100:>6.1f}%{mdd*100:>8.1f}%")
