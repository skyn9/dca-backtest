"""引擎自检：全部用已知答案校验，不依赖网络。"""

import numpy as np
import pandas as pd
import pytest

from dca.engine import dca_path, lumpsum_rolling, perf_stats, rolling_dca, xirr_monthly


def const_returns(n, r, start="2010-01-31"):
    return pd.Series([r] * n, index=pd.date_range(start, periods=n, freq="ME"))


@pytest.mark.parametrize("L,rm", [(12, 0.01), (36, 0.006), (60, 0.008), (120, 0.008), (240, 0.005)])
def test_xirr_exact_equal_cashflow(L, rm):
    """等额定投、固定月收益 -> IRR 必须精确等于 (1+rm)^12-1"""
    fv = sum(1000 * (1 + rm) ** (L - i) for i in range(L))
    assert xirr_monthly([1000.0] * L, fv) == pytest.approx((1 + rm) ** 12 - 1, abs=1e-9)


def test_xirr_exact_uneven_cashflow():
    rng = np.random.default_rng(0)
    L, rm = 60, 0.007
    cf = list(rng.uniform(500, 1500, L))
    fv = sum(c * (1 + rm) ** (L - i) for i, c in enumerate(cf))
    assert xirr_monthly(cf, fv) == pytest.approx((1 + rm) ** 12 - 1, abs=1e-9)


def test_xirr_zero_return():
    assert xirr_monthly([1000.0] * 24, 24000.0) == pytest.approx(0.0, abs=1e-9)


def test_dca_path_self_consistent():
    rm, n = 0.008, 60
    H, irr = dca_path(const_returns(n, rm), buy_fee=0.0)
    assert H["cost"].iloc[-1] == pytest.approx(60000.0)
    assert H["value"].iloc[-1] == pytest.approx(sum(1000 * (1 + rm) ** (n - i) for i in range(n)))
    assert irr == pytest.approx((1 + rm) ** 12 - 1, abs=1e-9)
    assert len(H) == n


def test_buy_fee_scales_value_not_cost():
    r = const_returns(60, 0.008)
    a, _ = dca_path(r, buy_fee=0.0)
    b, _ = dca_path(r, buy_fee=0.0012)
    assert b["value"].iloc[-1] / a["value"].iloc[-1] == pytest.approx(0.9988, abs=1e-9)
    assert b["cost"].iloc[-1] == pytest.approx(a["cost"].iloc[-1])


def test_annual_fee_direction_and_magnitude():
    """从月收益里扣年费 1.2% -> IRR 下降约 1.2~1.4pp（复利导致略大于 1.2）"""
    r = const_returns(60, 0.008)
    _, base = dca_path(r, buy_fee=0.0)
    _, feed = dca_path(r - 0.012 / 12, buy_fee=0.0)
    assert 0.010 < base - feed < 0.014


def test_rolling_window_count_and_span():
    r = const_returns(200, 0.006)
    for H in (36, 60, 120):
        rd = rolling_dca(r, horizon_m=H)
        assert len(rd) == 200 - H + 1
        span = (rd["end"].iloc[0].to_period("M") - rd["start"].iloc[0].to_period("M")).n
        assert span == H - 1


def test_rebalance_identical_for_single_asset():
    r = const_returns(150, 0.006)
    got = [rolling_dca(r, horizon_m=120, rebalance=m)["irr"].median() for m in ("cashflow", "annual", "none")]
    assert max(got) - min(got) < 1e-12


def test_cashflow_rebalance_pulls_toward_target():
    """一涨一跌两个资产：现金流再平衡后的末期权重必须比不平衡更接近 50/50"""
    idx = pd.date_range("2010-01-31", periods=48, freq="ME")
    R = pd.DataFrame({"up": [0.02] * 48, "down": [-0.01] * 48}, index=idx)
    dev = {}
    for mode in ("cashflow", "none"):
        units = np.zeros(2)
        for t in range(48):
            net = 1000.0
            tot = units.sum()
            if mode == "cashflow" and tot > 0:
                gap = np.maximum((tot + net) * np.array([0.5, 0.5]) - units, 0)
                alloc = gap / gap.sum() * net if gap.sum() > 1e-12 else net * np.array([0.5, 0.5])
            else:
                alloc = net * np.array([0.5, 0.5])
            units = (units + alloc) * (1 + R.iloc[t].values)
        dev[mode] = abs(units[0] / units.sum() - 0.5)
    assert dev["cashflow"] < dev["none"]


def test_contrib_growth_raises_cost_not_irr():
    r = const_returns(120, 0.007)
    a, ia = dca_path(r, buy_fee=0.0)
    b, ib = dca_path(r, buy_fee=0.0, contrib_growth=0.10)
    assert b["cost"].iloc[-1] > a["cost"].iloc[-1] * 1.4
    assert abs(ib - ia) < 1e-9  # 固定收益率下，递增定投不改变 IRR


def test_lumpsum_matches_cagr():
    rm = 0.008
    ls = lumpsum_rolling(const_returns(150, rm), horizon_m=120)
    assert ls.iloc[0] == pytest.approx((1 + rm) ** 12 - 1, abs=1e-9)


def test_perf_stats_cagr():
    rm = 0.008
    st = perf_stats(const_returns(120, rm).to_frame("x"))
    assert st["cagr"].iloc[0] == pytest.approx((1 + rm) ** 12 - 1, abs=1e-9)
    assert st["mdd"].iloc[0] == pytest.approx(0.0, abs=1e-12)


def test_cli_survives_non_utf8_console():
    """Windows 控制台默认 cp1252，中文输出曾导致 UnicodeEncodeError 崩溃。

    这是 CI 在 windows-latest 上抓到的真实缺陷，此测试防止回归。
    """
    import os
    import subprocess
    import sys

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    r = subprocess.run([sys.executable, "-m", "dca", "sources"], capture_output=True, env=env, timeout=60)
    assert r.returncode == 0, f"退出码 {r.returncode}: {r.stderr.decode('utf-8', 'replace')[-400:]}"
