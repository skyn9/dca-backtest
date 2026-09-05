# -*- coding: utf-8 -*-
"""组合与配置的自检，不依赖网络。"""
import glob
import numpy as np
import pandas as pd
import pytest

from dca import Portfolio
from dca.portfolio import Asset
from dca.sources import available


def test_weights_normalized():
    p = Portfolio.from_dict({"name": "t", "assets": [
        {"name": "a", "source": "fund", "code": "1", "weight": 2},
        {"name": "b", "source": "fund", "code": "2", "weight": 3}]})
    assert p.weights.sum() == pytest.approx(1.0)
    assert p.weights["a"] == pytest.approx(0.4)


def test_equal_weight_when_unspecified():
    p = Portfolio.from_dict({"name": "t", "assets": [
        {"name": "a", "source": "fund", "code": "1"},
        {"name": "b", "source": "fund", "code": "2"}]})
    assert p.weights["a"] == pytest.approx(0.5)


def test_proxy_resolution():
    a = Asset(name="x", source="fund", code="009051", weight=1.0,
              proxy={"source": "csindex", "code": "H00922", "annual_fee": 0.002})
    q = a.as_proxy()
    assert (q.source, q.code, q.annual_fee) == ("csindex", "H00922", 0.002)
    assert q.name == a.name and q.weight == a.weight
    assert Asset(name="y", source="fund", code="1").as_proxy().source == "fund"


def test_gross_drag_sums_fee_and_tracking():
    a = Asset(name="x", source="sina_fut", code="AU0", annual_fee=0.001, tracking_diff=0.003)
    assert a.gross_drag == pytest.approx(0.004)


@pytest.mark.parametrize("path", sorted(glob.glob("configs/**/*.yaml", recursive=True)))
def test_shipped_configs_are_valid(path):
    p = Portfolio.from_yaml(path)
    assert len(p.assets) >= 2
    assert p.weights.sum() == pytest.approx(1.0)
    for a in p.assets:
        assert a.source in available(), f"{path}: 未知数据源 {a.source}"
        assert 0 <= a.weight <= 1
        if a.proxy:
            assert a.proxy["source"] in available()


def test_blend_matches_manual_weighting():
    idx = pd.date_range("2020-01-31", periods=12, freq="ME")
    r = pd.DataFrame({"a": np.linspace(0.01, 0.02, 12), "b": np.linspace(-0.01, 0.01, 12)}, index=idx)
    p = Portfolio.from_dict({"name": "t", "assets": [
        {"name": "a", "source": "fund", "code": "1", "weight": 0.7},
        {"name": "b", "source": "fund", "code": "2", "weight": 0.3}]})
    assert np.allclose(p.blend(r).values, (r["a"] * 0.7 + r["b"] * 0.3).values)
