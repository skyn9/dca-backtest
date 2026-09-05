# -*- coding: utf-8 -*-
"""稳健性检验：样本外 / 权重扰动 / Block Bootstrap / 蒙特卡洛 / 压力情景。

这些是判断"回测结果是真规律还是过拟合"的工具，也是本项目最该被复用的部分。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from ..engine import rolling_dca, dca_path, xirr_monthly

__all__ = ["walk_forward", "weight_perturbation", "block_bootstrap",
           "monte_carlo", "stress_scenarios", "optimize_weights"]


def optimize_weights(returns: pd.DataFrame, *, horizon_y: int = 10, objective: str = "p10",
                     n_iter: int = 3000, max_weight: float = 0.35,
                     bounds: dict[str, tuple[float, float]] | None = None,
                     top_k: int = 40, seed: int = 0, **kw) -> tuple[np.ndarray, pd.DataFrame]:
    """随机搜索最优权重。

    objective: 'p10'(下行保护，推荐) | 'median' | 'min'
    bounds:    {资产名: (下限, 上限)} 施加有经济含义的约束
    返回 (top_k 均值权重, 全部候选的评分表)
    """
    rng = np.random.default_rng(seed)
    cols = list(returns.columns)
    H = horizon_y * 12
    lo = np.array([bounds.get(c, (0.0, 1.0))[0] if bounds else 0.0 for c in cols])
    hi = np.array([bounds.get(c, (0.0, max_weight))[1] if bounds else max_weight for c in cols])

    def score(w):
        pr = (returns * w).sum(axis=1)
        if len(pr) < H + 6:
            return -9.0
        i = rolling_dca(pr, None, H, **kw)["irr"].dropna()
        if not len(i):
            return -9.0
        return {"p10": i.quantile(.10), "median": i.median(), "min": i.min()}[objective]

    cands = []
    for _ in range(n_iter):
        w = rng.dirichlet(np.ones(len(cols)) * 0.9)
        if (w < lo).any() or (w > hi).any():
            continue
        cands.append((score(w), w))
    if not cands:
        raise RuntimeError("约束过紧，没有可行解")
    cands.sort(key=lambda x: -x[0])
    W = np.array([c[1] for c in cands[:top_k]])
    tab = pd.DataFrame([dict(zip(cols, w), score=s) for s, w in cands[:top_k]])
    return W.mean(axis=0), tab


def walk_forward(returns: pd.DataFrame, splits: list[tuple[str, str, str, str]],
                 fixed_weights=None, *, opt_horizon_y: int = 5, n_iter: int = 2500,
                 bounds=None, seed: int = 0, **kw) -> pd.DataFrame:
    """样本外检验：训练段优化权重 → 测试段实测。

    splits: [(训练起, 训练止, 测试起, 测试止), ...]
    fixed_weights: 你自己的固定方案，用于对照（过拟合的最强反证）
    """
    cols = list(returns.columns)
    eq = np.ones(len(cols)) / len(cols)
    rows = []
    for tr0, tr1, te0, te1 in splits:
        Rtr = returns.loc[tr0:tr1]
        Rte = returns.loc[te0:te1]
        if len(Rtr) < 48 or len(Rte) < 36:
            continue
        w_opt, _ = optimize_weights(Rtr, horizon_y=opt_horizon_y, n_iter=n_iter,
                                    bounds=bounds, seed=seed, **kw)
        def full_irr(R, w):
            res = dca_path((R * w).sum(axis=1), **kw)
            return res[1] if res else np.nan
        row = {"train": f"{tr0[:7]}~{tr1[:7]}", "test": f"{te0[:7]}~{te1[:7]}",
               "n_train": len(Rtr), "n_test": len(Rte),
               "opt_in": full_irr(Rtr, w_opt), "opt_out": full_irr(Rte, w_opt),
               "equal_out": full_irr(Rte, eq), "weights": w_opt}
        if fixed_weights is not None:
            fw = np.asarray([fixed_weights[c] for c in cols] if hasattr(fixed_weights, "__getitem__")
                            and not isinstance(fixed_weights, np.ndarray) else fixed_weights, float)
            fw = fw / fw.sum()
            row["fixed_in"] = full_irr(Rtr, fw)
            row["fixed_out"] = full_irr(Rte, fw)
            row["opt_minus_fixed"] = row["opt_out"] - row["fixed_out"]
        rows.append(row)
    return pd.DataFrame(rows)


def weight_perturbation(returns: pd.DataFrame, weights, *, horizon_y: int = 10,
                        levels=(0.03, 0.05, 0.08), n: int = 150, seed: int = 0, **kw) -> pd.DataFrame:
    """权重扰动：随机推移权重，看结论是否依赖精确权重。"""
    rng = np.random.default_rng(seed)
    cols = list(returns.columns)
    w0 = np.asarray([weights[c] for c in cols] if hasattr(weights, "__getitem__")
                    and not isinstance(weights, np.ndarray) else weights, float)
    w0 = w0 / w0.sum()
    H = horizon_y * 12

    def stat(w):
        i = rolling_dca((returns * w).sum(axis=1), None, H, **kw)["irr"].dropna()
        return (float(i.median()), float(i.min())) if len(i) else (np.nan, np.nan)

    base_med, base_min = stat(w0)
    rows = [{"level": "基准", "med_mean": base_med, "med_lo": base_med, "med_hi": base_med,
             "min_mean": base_min, "all_positive": base_min > 0, "n": 1}]
    for lv in levels:
        ms, mn = [], []
        for _ in range(n):
            w = np.clip(w0 + rng.uniform(-lv, lv, len(w0)), 0.005, None)
            a, b = stat(w / w.sum())
            ms.append(a); mn.append(b)
        rows.append({"level": f"±{lv*100:.0f}pp", "med_mean": float(np.mean(ms)),
                     "med_lo": float(np.min(ms)), "med_hi": float(np.max(ms)),
                     "min_mean": float(np.mean(mn)),
                     "all_positive": bool(np.all(np.array(mn) > 0)), "n": n})
    df = pd.DataFrame(rows)
    df["vs_base"] = df["med_mean"] - base_med
    return df


def block_bootstrap(series: pd.Series, *, horizon_y: int = 10, block: int = 12,
                    n_paths: int = 4000, monthly: float = 1000.0, buy_fee: float = 0.0012,
                    seed: int = 0) -> pd.Series:
    """按块重采样保留自相关，生成"平行历史"。比滚动窗口更严苛。"""
    rng = np.random.default_rng(seed)
    arr = series.values
    T = len(arr)
    H = horizon_y * 12
    nb = int(np.ceil(H / block))
    if T <= block + 1:
        raise ValueError("序列太短")
    out = np.empty(n_paths)
    for k in range(n_paths):
        idx = rng.integers(0, T - block, nb)
        seq = np.concatenate([arr[i:i + block] for i in idx])[:H]
        v = np.concatenate([[1.0], np.cumprod(1 + seq)])
        units = (monthly * (1 - buy_fee) / v[:H]).sum()
        out[k] = xirr_monthly([monthly] * H, units * v[H])
    return pd.Series(out).dropna()


def monte_carlo(returns: pd.DataFrame, weights, *, years: int = 20, n_paths: int = 6000,
                shock: dict[str, float] | None = None, monthly: float = 1000.0,
                buy_fee: float = 0.0012, seed: int = 0) -> pd.Series:
    """前瞻模拟：保留资产间协方差结构，按历史均值（可加冲击）模拟未来。

    shock: {资产名: 乘数}，例如 {'美股': 0.6} 表示该资产未来均值只有历史的 60%
    """
    rng = np.random.default_rng(seed)
    cols = list(returns.columns)
    mu = returns.mean().values.copy()
    if shock:
        for i, c in enumerate(cols):
            if c in shock:
                mu[i] *= shock[c]
    cov = returns.cov().values
    L = np.linalg.cholesky(cov + np.eye(len(cols)) * 1e-12)
    w = np.asarray([weights[c] for c in cols] if hasattr(weights, "__getitem__")
                   and not isinstance(weights, np.ndarray) else weights, float)
    w = w / w.sum()
    M = years * 12
    out = np.empty(n_paths)
    for k in range(n_paths):
        r = mu + rng.standard_normal((M, len(cols))) @ L.T
        pr = r @ w
        v = np.concatenate([[1.0], np.cumprod(1 + pr)])
        units = (monthly * (1 - buy_fee) / v[:M]).sum()
        out[k] = xirr_monthly([monthly] * M, units * v[M])
    return pd.Series(out).dropna()


def stress_scenarios(returns: pd.DataFrame, weights, scenarios: dict[str, dict[str, float]],
                     *, horizon_y: int = 10, **kw) -> pd.DataFrame:
    """收益率压力情景：对指定资产的月均收益做平移，保留波动与相关结构。

    scenarios: {情景名: {资产名: 年化调整值}}，如 {'美股-6%': {'标普500': -0.06}}
    """
    H = horizon_y * 12
    rows = []
    for tag, adj in scenarios.items():
        R = returns.copy()
        for c, v in (adj or {}).items():
            if c in R.columns:
                R[c] = R[c] + v / 12.0
        i = rolling_dca((R * np.asarray([weights[c] for c in R.columns])).sum(axis=1),
                        None, H, **kw)["irr"].dropna()
        rows.append({"scenario": tag, "med": float(i.median()), "p10": float(i.quantile(.1)),
                     "min": float(i.min()), "loss": float((i < 0).mean())})
    return pd.DataFrame(rows)
