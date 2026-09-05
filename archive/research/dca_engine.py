# -*- coding: utf-8 -*-
"""定投(DCA)回测引擎：月度定投 + 现金流再平衡 + 费率 + 滚动窗口 IRR 分布。"""
import numpy as np, pandas as pd
from scipy.optimize import brentq

def xirr_monthly(cashflows, final_value):
    """cashflows: 每月投入(正数=流出)，final_value: 期末市值。返回年化 IRR。"""
    n = len(cashflows)
    def npv(r):
        m = (1 + r) ** (1/12.0)
        return sum(-cf / m**i for i, cf in enumerate(cashflows)) + final_value / m**n
    try:
        lo, hi = -0.95, 3.0
        if npv(lo) * npv(hi) > 0: return np.nan
        return brentq(npv, lo, hi, maxiter=200, xtol=1e-10)
    except Exception:
        return np.nan

def dca_path(px, weights, annual_fee=None, buy_fee=0.0012, rebalance="cashflow", monthly=1000.0):
    """px: DataFrame 月度价格(净值), weights: dict 或 Series 目标权重
       annual_fee: dict 每资产年费率(小数)，None 表示价格已含费
       buy_fee: 申购费(小数)  rebalance: 'cashflow'(用新钱调仓) / 'annual' / 'none'
       返回: DataFrame(每月: 累计投入 cost, 市值 value), 以及最终 IRR"""
    cols = list(weights.index if hasattr(weights, "index") else weights.keys())
    w = np.array([weights[c] for c in cols], dtype=float); w = w / w.sum()
    P = px[cols].dropna().values
    n, k = P.shape
    if n < 13: return None
    ret = P[1:] / P[:-1] - 1.0                      # 月度收益
    if annual_fee is not None:                      # 指数需扣模拟费率
        f = np.array([annual_fee.get(c, 0.0) for c in cols])
        ret = ret - (f / 12.0)
    units = np.zeros(k)                             # 各资产持有市值(直接用金额建模)
    cost, cf = 0.0, []
    hist = []
    for t in range(n - 1):
        # t 时点买入
        net = monthly * (1 - buy_fee)
        if rebalance == "cashflow" and units.sum() > 0:
            tgt = (units.sum() + net) * w
            gap = np.maximum(tgt - units, 0)
            alloc = (gap / gap.sum() * net) if gap.sum() > 1e-12 else net * w
        else:
            alloc = net * w
        units = units + alloc
        cost += monthly; cf.append(monthly)
        # t -> t+1 增长
        units = units * (1 + ret[t])
        if rebalance == "annual" and (t + 1) % 12 == 0:
            units = units.sum() * w
        hist.append((cost, units.sum()))
    H = pd.DataFrame(hist, columns=["cost", "value"], index=px[cols].dropna().index[1:n])
    irr = xirr_monthly(cf, units.sum())
    return H, irr

def rolling_dca(px, weights, horizon_m, **kw):
    """所有可能起点，定投 horizon_m 个月的 IRR 与终值/成本比"""
    cols = list(weights.index if hasattr(weights, "index") else weights.keys())
    d = px[cols].dropna()
    out = []
    for s in range(0, len(d) - horizon_m):
        sub = d.iloc[s:s + horizon_m + 1]
        r = dca_path(sub, weights, **kw)
        if r is None: continue
        H, irr = r
        out.append(dict(start=sub.index[0], end=sub.index[-1], irr=irr,
                        mult=H["value"].iloc[-1] / H["cost"].iloc[-1],
                        maxdd=(H["value"] / H["cost"] - 1).min()))
    return pd.DataFrame(out)

def summarize(rd, label=""):
    if rd is None or len(rd) == 0: return {}
    i = rd["irr"].dropna()
    return dict(label=label, n=len(i), irr_med=i.median(), irr_mean=i.mean(),
                irr_p10=i.quantile(.10), irr_p25=i.quantile(.25), irr_p75=i.quantile(.75),
                irr_p90=i.quantile(.90), irr_min=i.min(), irr_max=i.max(),
                loss_prob=(i < 0).mean(), below4=(i < 0.04).mean(),
                worst_mult=rd["mult"].min(), med_mult=rd["mult"].median(),
                med_maxdd=rd["maxdd"].median(), worst_maxdd=rd["maxdd"].min())

def perf_stats(px, annual_fee=None):
    """单资产统计: CAGR / 年化波动 / 最大回撤 / Sharpe"""
    out = []
    for c in px.columns:
        s = px[c].dropna()
        if len(s) < 24: continue
        r = s.pct_change().dropna()
        if annual_fee: r = r - annual_fee.get(c, 0.0)/12.0
        yrs = len(r)/12.0
        cagr = (1+r).prod()**(1/yrs) - 1
        vol = r.std()*np.sqrt(12)
        cum = (1+r).cumprod(); dd = (cum/cum.cummax()-1).min()
        out.append(dict(asset=c, start=str(s.index[0].date()), yrs=round(yrs,1),
                        cagr=cagr, vol=vol, mdd=dd, sharpe=(cagr-0.02)/vol if vol>0 else np.nan))
    return pd.DataFrame(out)
