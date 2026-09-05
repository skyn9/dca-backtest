# -*- coding: utf-8 -*-
import sys, time, itertools; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
FEE={"A股沪深300":0.0020,"A股中证500":0.0020,"A股红利":0.0020,"A股上证50":0.0020,
     "A股中证1000":0.0020,"债券中证全债":0.0030,"美股标普500(人民币)":0.0065,"美股纳斯达克(人民币)":0.0065}
HS,C5,DIV,B,SP,NQ = "A股沪深300","A股中证500","A股红利","债券中证全债","美股标普500(人民币)","美股纳斯达克(人民币)"

PORT = {
 "①全仓沪深300(大众默认)":      {HS:1.0},
 "②全仓A股红利":               {DIV:1.0},
 "③经典60/40(沪深300+债)":     {HS:.6, B:.4},
 "④A股均衡(300+500+红利)":     {HS:.34, C5:.33, DIV:.33},
 "⑤中美对半(300+标普)":         {HS:.5, SP:.5},
 "⑥全球均衡5资产":              {HS:.2, DIV:.2, SP:.2, NQ:.2, B:.2},
 "⑦红利+美股+债":              {DIV:.35, SP:.20, NQ:.20, B:.25},
 "⑧股80债20全球":              {DIV:.25, HS:.15, SP:.20, NQ:.20, B:.20},
 "⑨激进全球股票":               {DIV:.30, C5:.10, SP:.25, NQ:.35},
 "⑩纳指单押":                  {NQ:1.0},
}
def port_px(w):
    """把组合当成一个再平衡后的合成资产（月度再平衡）"""
    cols=list(w.keys()); ww=np.array([w[c] for c in cols]); ww=ww/ww.sum()
    r=A[cols].pct_change().dropna()
    r=r - np.array([FEE.get(c,0) for c in cols])/12.0
    pr=(r*ww).sum(axis=1)
    return pd.DataFrame({"P":(1+pr).cumprod()})

t0=time.time()
for H,hn in [(60,"5年"),(120,"10年"),(180,"15年")]:
    print(f"\n{'='*118}\n【组合定投 {hn}】长窗口2005-2026 · 月定投 · 现金流再平衡 · 申购费0.12% · 已扣年化管理费")
    print(f"{'组合':<26}{'样本':>5}{'中位IRR':>9}{'10%分位':>9}{'25%分位':>9}{'75%分位':>9}{'最差':>8}{'亏损率':>8}{'中位终值':>9}{'最差终值':>9}")
    res=[]
    for name,w in PORT.items():
        px=port_px(w); ws=pd.Series({"P":1.0})
        rd=E.rolling_dca(px, ws, H, annual_fee=None, buy_fee=0.0012)
        s=E.summarize(rd,name)
        if not s: continue
        res.append(s)
        print(f"{name:<26}{s['n']:>5}{s['irr_med']*100:>8.2f}%{s['irr_p10']*100:>8.2f}%{s['irr_p25']*100:>8.2f}%"
              f"{s['irr_p75']*100:>8.2f}%{s['irr_min']*100:>7.2f}%{s['loss_prob']*100:>7.1f}%{s['med_mult']:>8.2f}x{s['worst_mult']:>8.2f}x")
print(f"\n耗时 {time.time()-t0:.1f}s")
