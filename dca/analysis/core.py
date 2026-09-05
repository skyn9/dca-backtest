"""核心分析：滚动窗口 / 起点敏感性 / 全周期矩阵。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..engine import dca_path, lumpsum_rolling, rolling_dca, summarize

DEFAULT_HORIZONS = (3, 5, 10, 15)


def rolling_table(returns, weights=None, horizons=DEFAULT_HORIZONS, **kw) -> pd.DataFrame:
    """多期限滚动定投汇总。"""
    rows = []
    for y in horizons:
        H = y * 12
        if len(returns) < H + 6:
            continue
        s = summarize(rolling_dca(returns, weights, H, **kw), f"{y}年")
        if s:
            s["years"] = y
            rows.append(s)
    return pd.DataFrame(rows)


def start_sensitivity(
    returns_by_start: dict[str, pd.DataFrame], weights=None, horizon_y: int = 10, **kw
) -> pd.DataFrame:
    """起点敏感性：同一组合在多个起点窗口下的结果。

    returns_by_start: {窗口标签: 收益率矩阵}
    返回每个窗口的中位/最差/亏损率，以及跨窗口的极差。
    """
    rows = []
    for tag, r in returns_by_start.items():
        H = horizon_y * 12
        if len(r) < H + 6:
            rows.append({"window": tag, "med": np.nan, "min": np.nan, "loss": np.nan, "n": 0})
            continue
        s = summarize(rolling_dca(r, weights, H, **kw))
        rows.append(
            {
                "window": tag,
                "med": s["med"],
                "p10": s["p10"],
                "min": s["min"],
                "loss": s["loss_prob"],
                "n": s["n"],
            }
        )
    df = pd.DataFrame(rows)
    ok = df["med"].dropna()
    if len(ok):
        df.attrs["range"] = float(ok.max() - ok.min())
        df.attrs["lo"], df.attrs["hi"] = float(ok.min()), float(ok.max())
    return df


def asset_start_sensitivity(
    portfolio,
    windows: dict[str, str],
    horizon_y: int = 10,
    include_portfolio: bool = True,
    use_proxy: bool = False,
    **kw,
) -> pd.DataFrame:
    """逐资产 + 组合的起点敏感性对照表（本项目最有信息量的一张表）。

    windows: {标签: 起始日期字符串}
    """
    px = portfolio.monthly(use_proxy=use_proxy)
    rows = []
    names = [a.name for a in portfolio.resolved(use_proxy)]
    for nm in names:
        a = portfolio.asset(nm, use_proxy=use_proxy)
        vals = []
        for st in windows.values():
            s = px[nm].dropna()
            s = s[s.index >= st]
            r = s.pct_change().dropna() - a.gross_drag / 12.0
            H = horizon_y * 12
            if len(r) < H + 6:
                vals.append(np.nan)
                continue
            rd = rolling_dca(r, None, H, **kw)
            vals.append(float(rd["irr"].median()) if len(rd) else np.nan)
        rows.append({"name": nm, "kind": "asset", **dict(zip(windows, vals, strict=True))})
    if include_portfolio:
        vals = []
        for st in windows.values():
            r = portfolio.returns(start=st, use_proxy=use_proxy)
            H = horizon_y * 12
            if len(r) < H + 6:
                vals.append(np.nan)
                continue
            rd = rolling_dca(r, portfolio.weights, H, **kw)
            vals.append(float(rd["irr"].median()) if len(rd) else np.nan)
        rows.append(
            {"name": f"★ {portfolio.name}", "kind": "portfolio", **dict(zip(windows, vals, strict=True))}
        )
    df = pd.DataFrame(rows)
    vc = [c for c in df.columns if c not in ("name", "kind")]
    df["lo"] = df[vc].min(axis=1)
    df["hi"] = df[vc].max(axis=1)
    df["range"] = df["hi"] - df["lo"]
    return df.sort_values("range")


def year_horizon_matrix(
    returns, weights=None, years=None, horizons=(1, 2, 3, 5, 7, 10, 15), **kw
) -> pd.DataFrame:
    """全周期矩阵：每个起投年（1 月） × 每种持有期限。"""
    idx = returns.index
    if years is None:
        years = sorted({d.year for d in idx})
    out = {}
    for y in years:
        pos = [i for i, d in enumerate(idx) if d.year == y and d.month == 1]
        if not pos:
            continue
        s = pos[0]
        row = {}
        for h in horizons:
            H = h * 12
            if s + H > len(returns):
                row[h] = np.nan
                continue
            res = dca_path(returns.iloc[s : s + H], weights, **kw)
            row[h] = res[1] if res else np.nan
        if not all(np.isnan(v) for v in row.values()):
            out[y] = row
    return pd.DataFrame(out).T


def dca_vs_lumpsum(returns, weights=None, horizons=DEFAULT_HORIZONS, **kw) -> pd.DataFrame:
    """定投 vs 一次性投入。"""
    rows = []
    for y in horizons:
        H = y * 12
        if len(returns) < H + 6:
            continue
        rd = rolling_dca(returns, weights, H, **kw)
        ls = lumpsum_rolling(returns, weights, H)
        if rd.empty or ls.empty:
            continue
        rows.append(
            {
                "years": y,
                "dca_med": float(rd["irr"].median()),
                "lump_med": float(ls.median()),
                "dca_min": float(rd["irr"].min()),
                "lump_min": float(ls.min()),
                "dca_loss": float((rd["irr"] < 0).mean()),
                "lump_loss": float((ls < 0).mean()),
            }
        )
    return pd.DataFrame(rows)
