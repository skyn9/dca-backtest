# -*- coding: utf-8 -*-
"""定投回测引擎。所有收益率均为 IRR（按现金流时点加权），非"总收益÷总投入"。"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import brentq

__all__ = ["xirr_monthly", "dca_path", "rolling_dca", "lumpsum_rolling", "summarize", "perf_stats"]


def xirr_monthly(cashflows, final_value: float) -> float:
    """等间隔（月）现金流的年化内部收益率。

    cashflows[i] 发生在第 i 个月（i=0..n-1，正数=投入），
    final_value 发生在第 n 个月（最后一笔投入后再过一个月）。
    """
    n = len(cashflows)
    if n == 0:
        return float("nan")

    def npv(r):
        m = (1.0 + r) ** (1.0 / 12.0)
        return sum(-cf / m ** i for i, cf in enumerate(cashflows)) + final_value / m ** n

    try:
        lo, hi = -0.95, 5.0
        if npv(lo) * npv(hi) > 0:
            return float("nan")
        return brentq(npv, lo, hi, maxiter=250, xtol=1e-12)
    except Exception:
        return float("nan")


def dca_path(returns: pd.DataFrame | pd.Series, weights=None, *, monthly: float = 1000.0,
             buy_fee: float = 0.0012, rebalance: str = "cashflow",
             contrib_growth: float = 0.0, dip_boost: float = 0.0):
    """在给定的月度收益率序列上做定投。

    returns   : DataFrame(多资产) 或 Series(已合成)
    rebalance : 'cashflow' 用新钱补低配 | 'annual' 每 12 期重置 | 'none' 不管
    contrib_growth : 每年投入递增比例，如 0.10
    dip_boost : 相对近 12 期高点每跌 10% 追加的倍数，0 表示不加码

    返回 (history: DataFrame[cost, value], irr: float)
    """
    if isinstance(returns, pd.Series):
        returns = returns.to_frame("P")
    R = returns.values
    n, k = R.shape
    if n < 2:
        return None
    if weights is None:
        w = np.ones(k) / k
    else:
        w = np.asarray([weights[c] for c in returns.columns] if hasattr(weights, "__getitem__")
                       and not isinstance(weights, np.ndarray) else weights, dtype=float)
        w = w / w.sum()

    units = np.zeros(k)
    cost = 0.0
    cf: list[float] = []
    hist = []
    nav = 1.0
    peak = 1.0
    for t in range(n):
        amt = monthly * (1 + contrib_growth) ** (t / 12.0)
        if dip_boost:
            dd = nav / peak - 1.0
            amt *= 1.0 + dip_boost * max(0.0, -dd) / 0.10
        net = amt * (1 - buy_fee)
        tot = units.sum()
        if rebalance == "cashflow" and tot > 0:
            gap = np.maximum((tot + net) * w - units, 0.0)
            alloc = gap / gap.sum() * net if gap.sum() > 1e-12 else net * w
        else:
            alloc = net * w
        units += alloc
        cost += amt
        cf.append(amt)
        units *= (1.0 + R[t])
        nav *= (1.0 + float((R[t] * w).sum()))
        peak = max(peak, nav)
        if rebalance == "annual" and (t + 1) % 12 == 0 and units.sum() > 0:
            units = units.sum() * w
        hist.append((cost, units.sum()))

    H = pd.DataFrame(hist, columns=["cost", "value"], index=returns.index)
    return H, xirr_monthly(cf, units.sum())


def rolling_dca(returns, weights=None, horizon_m: int = 120, *, step: int = 1, **kw) -> pd.DataFrame:
    """所有可能起点、固定期限的定投结果。"""
    if isinstance(returns, pd.Series):
        returns = returns.to_frame("P")
    out = []
    for s in range(0, len(returns) - horizon_m + 1, step):
        sub = returns.iloc[s:s + horizon_m]
        if len(sub) < horizon_m:
            break
        res = dca_path(sub, weights, **kw)
        if res is None:
            continue
        H, irr = res
        if irr != irr:
            continue
        out.append({"start": sub.index[0], "end": sub.index[-1], "irr": irr,
                    "mult": H["value"].iloc[-1] / H["cost"].iloc[-1],
                    "maxdd": float((H["value"] / H["cost"] - 1).min())})
    return pd.DataFrame(out)


def lumpsum_rolling(returns, weights=None, horizon_m: int = 120) -> pd.Series:
    """同期限一次性投入的年化收益，用于与定投对比。"""
    if isinstance(returns, pd.DataFrame):
        w = np.ones(returns.shape[1]) / returns.shape[1] if weights is None else \
            np.asarray([weights[c] for c in returns.columns], dtype=float)
        r = (returns * (w / w.sum())).sum(axis=1)
    else:
        r = returns
    v = np.concatenate([[1.0], np.cumprod(1 + r.values)])
    out = [(v[s + horizon_m] / v[s]) ** (12.0 / horizon_m) - 1
           for s in range(0, len(v) - horizon_m)]
    return pd.Series(out, index=r.index[:len(out)])


def summarize(rd: pd.DataFrame, label: str = "") -> dict:
    if rd is None or rd.empty:
        return {}
    i = rd["irr"].dropna()
    return {"label": label, "n": len(i), "med": float(i.median()), "mean": float(i.mean()),
            "p10": float(i.quantile(.10)), "p25": float(i.quantile(.25)),
            "p75": float(i.quantile(.75)), "p90": float(i.quantile(.90)),
            "min": float(i.min()), "max": float(i.max()),
            "loss_prob": float((i < 0).mean()),
            "med_mult": float(rd["mult"].median()), "worst_mult": float(rd["mult"].min()),
            "med_maxdd": float(rd["maxdd"].median()), "worst_maxdd": float(rd["maxdd"].min())}


def perf_stats(returns: pd.DataFrame) -> pd.DataFrame:
    """单资产（或合成序列）的持有期统计：CAGR / 波动 / 最大回撤 / Sharpe。"""
    if isinstance(returns, pd.Series):
        returns = returns.to_frame("P")
    rows = []
    for c in returns.columns:
        r = returns[c].dropna()
        if len(r) < 24:
            continue
        yrs = len(r) / 12.0
        cagr = float((1 + r).prod() ** (1 / yrs) - 1)
        vol = float(r.std() * np.sqrt(12))
        cum = (1 + r).cumprod()
        rows.append({"asset": c, "months": len(r), "years": round(yrs, 1), "cagr": cagr,
                     "vol": vol, "mdd": float((cum / cum.cummax() - 1).min()),
                     "sharpe": (cagr - 0.02) / vol if vol > 0 else float("nan")})
    return pd.DataFrame(rows)
