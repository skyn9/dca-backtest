# -*- coding: utf-8 -*-
"""简化版 vs 完整版：少几只基金会损失多少？"""
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
FEE={"A股沪深300":.0020,"A股中证500":.0020,"A股红利":.0020,"债券中证全债":.0030,
     "美股标普500(人民币)":.0065,"美股纳斯达克(人民币)":.0065,"港股红利TR":.0060}
L=["A股红利","A股沪深300","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","债券中证全债"]
R=A[L].pct_change().dropna()-np.array([FEE[c] for c in L])/12.0
V={  # 长窗口无黄金，权重等比放大
 "完整版7只(不含黄金部分)": [.22,.08,.05,.10,.18,.15,.10],
 "简化5只(去中证500/300合并)":[.25,.08,.00,.10,.20,.15,.12],
 "极简4只(红利+标普+纳指+债)":[.32,.00,.00,.00,.22,.16,.20],
 "极简3只(红利+标普500+债)": [.40,.00,.00,.00,.38,.00,.22],
 "懒人2只(红利+标普500)":    [.55,.00,.00,.00,.45,.00,.00],
}
def ev(w,H):
    w=np.array(w); w=w/w.sum()
    pr=(R*w).sum(axis=1); px=pd.DataFrame({"P":(1+pr).cumprod()})
    rd=E.rolling_dca(px,pd.Series({"P":1.0}),H,annual_fee=None,buy_fee=0.0012)
    i=rd["irr"].dropna()
    return i.median(),i.quantile(.1),i.min(),(i<0).mean(),rd["maxdd"].median()
for H,hn in [(60,"5年"),(120,"10年"),(180,"15年")]:
    print(f"\n--- 定投{hn} (长窗口21.7年，不含黄金) ---")
    print(f"{'方案':<28}{'中位IRR':>9}{'10%分位':>9}{'最差':>9}{'亏损率':>8}{'中位浮亏':>9}")
    for nm,w in V.items():
        m,p,mn,lp,dd=ev(w,H)
        print(f"{nm:<28}{m*100:>8.2f}%{p*100:>8.2f}%{mn*100:>8.2f}%{lp*100:>7.1f}%{dd*100:>8.1f}%")
