import sys, time; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
FEE={"A股沪深300":0.0020,"A股中证500":0.0020,"A股红利":0.0020,"A股上证50":0.0020,
     "A股中证1000":0.0020,"债券中证全债":0.0030,"美股标普500(人民币)":0.0065,"美股纳斯达克(人民币)":0.0065}
t0=time.time()
print("【单资产 定投 滚动窗口 IRR 分布】长窗口 2005-2026，月定投，申购费0.12%，已扣年化费率\n")
for H,hn in [(60,"5年"),(120,"10年"),(180,"15年")]:
    print(f"--- 定投 {hn} ({H}个月) ---")
    print(f"{'资产':<20}{'样本':>5}{'中位IRR':>9}{'10%分位':>9}{'25%分位':>9}{'75%分位':>9}{'最差':>8}{'亏损概率':>9}{'中位终值/成本':>12}")
    rows=[]
    for c in A.columns:
        w=pd.Series({c:1.0})
        rd=E.rolling_dca(A[[c]], w, H, annual_fee=FEE, buy_fee=0.0012)
        s=E.summarize(rd,c)
        if not s: continue
        rows.append(s)
        print(f"{c:<20}{s['n']:>5}{s['irr_med']*100:>8.2f}%{s['irr_p10']*100:>8.2f}%{s['irr_p25']*100:>8.2f}%"
              f"{s['irr_p75']*100:>8.2f}%{s['irr_min']*100:>7.2f}%{s['loss_prob']*100:>8.1f}%{s['med_mult']:>11.2f}x")
    print()
print(f"耗时 {time.time()-t0:.1f}s")
