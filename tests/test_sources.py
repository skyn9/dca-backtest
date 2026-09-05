# -*- coding: utf-8 -*-
"""数据源注册与清洗逻辑，不发起网络请求。"""
import pandas as pd
import pytest
from dca.sources import available
from dca.sources.base import Source, MIN_GAP


def test_expected_sources_registered():
    keys = set(available())
    assert {"fund", "csindex", "sina_us", "sina_hk", "sina_fut", "akshare"} <= keys


def test_throttle_default_is_polite():
    assert MIN_GAP >= 3.0, "对公开接口的默认间隔不得低于 3 秒"


def test_clean_drops_base_placeholder():
    """中证指数常带一行远早于正式序列的基期占位，必须被剔除"""
    df = pd.DataFrame({
        "date": pd.to_datetime(["1990-01-01", "2004-12-31", "2005-01-04", "2005-01-05"]),
        "px": [1000.0, 1000.0, 982.79, 990.0]})
    out = Source._clean(df)
    assert out["date"].min() == pd.Timestamp("2004-12-31")
    assert len(out) == 3


def test_clean_keeps_continuous_series():
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=50, freq="D"),
                       "px": range(50)})
    assert len(Source._clean(df)) == 50
