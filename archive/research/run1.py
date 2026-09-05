import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
pd.set_option("display.width",200)
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
B=pd.read_parquet(f"{ROOT}/data/monthly_funds.parquet")
FEE={"A股沪深300":0.0020,"A股中证500":0.0020,"A股红利":0.0020,"A股上证50":0.0020,
     "A股中证1000":0.0020,"债券中证全债":0.0030,"美股标普500(人民币)":0.0065,"美股纳斯达克(人民币)":0.0065}
print("="*100); print("【长窗口 2004-12 ~ 2026-09，21.75年】指数全收益，已扣模拟基金费率")
s=E.perf_stats(A,FEE).sort_values("cagr",ascending=False)
for _,r in s.iterrows():
    print(f"{r['asset']:20s} {r['yrs']:5.1f}y  CAGR={r['cagr']*100:6.2f}%  年化波动={r['vol']*100:5.1f}%  最大回撤={r['mdd']*100:6.1f}%  Sharpe={r['sharpe']:.2f}")
print("\n"+"="*100); print("【实盘基金窗口】真实复权净值（已含全部费用/汇率/跟踪误差）")
s2=E.perf_stats(B).sort_values("cagr",ascending=False)
for _,r in s2.iterrows():
    print(f"{r['asset']:14s} 起{r['start']} {r['yrs']:5.1f}y  CAGR={r['cagr']*100:6.2f}%  波动={r['vol']*100:5.1f}%  最大回撤={r['mdd']*100:6.1f}%  Sharpe={r['sharpe']:.2f}")
print("\n"+"="*100); print("【相关性矩阵】长窗口月度收益")
print((A.pct_change().corr()*100).round(0).astype(int).to_string())
print("\n【相关性矩阵】实盘窗口 2013-09 起")
Bc=B.drop(columns=["A股创业板","德国DAX"]).dropna()
print(f"公共窗口 {Bc.index.min().date()} ~ {Bc.index.max().date()}  n={len(Bc)}")
print((Bc.pct_change().corr()*100).round(0).astype(int).to_string())
