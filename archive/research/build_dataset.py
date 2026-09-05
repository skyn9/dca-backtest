# -*- coding: utf-8 -*-
"""构建两套月度收益矩阵：
   A) 长窗口(2005~) 指数级别，含全收益指数+海外指数+汇率
   B) 实盘窗口(2013~) 真实可买基金复权净值（已含费率/汇率/跟踪误差）
"""
import sys, os, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch, akshare as ak
ROOT = "/Users/sky/PycharmProjects/DCA"

def to_month_end(df, col):
    d = df[["date", col]].dropna().copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date").sort_index()
    return d[col].resample("ME").last()

# ---------- B) 实盘基金窗口 ----------
FUNDS = {
 "A股沪深300":  "110020",   # 易方达沪深300ETF联接A  2009-08
 "A股中证500":  "161017",   # 富国中证500指数A       2011-10
 "A股创业板":    "001592",   # 天弘创业板ETF联接A     2015-06
 "A股红利":     "100032",   # 富国中证红利指数增强    2008-12
 "港股恒生":     "000071",   # 华夏恒生ETF联接A       2012-08
 "美股标普500":  "050025",   # 博时标普500ETF联接A    2012-06
 "美股纳指100":  "160213",   # 国泰纳斯达克100        2010-04
 "德国DAX":    "000614",   # 华安德国30联接         2014-08
 "黄金":       "000216",   # 华安黄金ETF联接A       2013-08
 "债券":       "110017",   # 易方达增强回报A        2008-03
}
ser = {}
for name, code in FUNDS.items():
    df, meta = fetch.fund_hist(code)
    s = to_month_end(df, "adj")
    ser[name] = s
    print(f"{name:12s} {code}  {s.index.min().date()} ~ {s.index.max().date()}  n={len(s)}")
B = pd.DataFrame(ser)
B.to_parquet(f"{ROOT}/data/monthly_funds.parquet")
print("\n[B] 实盘矩阵", B.shape, " 全齐起点:", B.dropna().index.min().date())

# ---------- A) 长窗口指数 ----------
IDX_CS = {"A股沪深300":"H00300","A股中证500":"H00905","A股红利":"H00922",
          "A股上证50":"H00016","债券中证全债":"H11001","A股中证1000":"H00852"}
a = {}
for name, code in IDX_CS.items():
    d = fetch.csindex(code)
    d = d[d["date"] >= "2004-12-01"]
    a[name] = to_month_end(d, "px")
    print(f"{name:12s} {code} {a[name].index.min().date()}~{a[name].index.max().date()} n={len(a[name])}")

# 美股指数 + 汇率 -> 人民币计价全收益
us = {}
for name, sym, div in [("美股标普500", ".INX", 1.90), ("美股纳斯达克", ".IXIC", 0.90)]:
    d = ak.index_us_stock_sina(symbol=sym)[["date", "close"]]
    d.columns = ["date", "px"]
    s = to_month_end(d, "px")
    # 加回股息（年化 div%，按月复利）
    n = np.arange(len(s))
    s = s * (1 + div/100.0) ** (n/12.0)
    us[name] = s
    print(f"{name:12s} {sym} {s.index.min().date()}~{s.index.max().date()} n={len(s)} 股息补偿{div}%/y")

fx = ak.currency_boc_safe()[["日期", "美元"]].rename(columns={"日期":"date","美元":"px"})
fx["date"] = pd.to_datetime(fx["date"]); fx["px"] = pd.to_numeric(fx["px"], errors="coerce")/100.0  # 100美元兑人民币 -> 1美元
fxm = to_month_end(fx, "px")
print(f"USDCNY  {fxm.index.min().date()}~{fxm.index.max().date()} 最新={fxm.iloc[-1]:.4f}")
for k, v in us.items():
    a[k + "(人民币)"] = (v * fxm.reindex(v.index).ffill()).dropna()

A = pd.DataFrame(a)
A = A[A.index >= "2004-12-31"]
A.to_parquet(f"{ROOT}/data/monthly_index.parquet")
print("\n[A] 长窗口矩阵", A.shape, " 全齐起点:", A.dropna().index.min().date(), "~", A.dropna().index.max().date())
print(A.dropna().head(2).to_string())
print(A.dropna().tail(2).to_string())
