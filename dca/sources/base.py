"""数据源抽象层：统一接口 + 本地缓存 + 全局节流。

新增一个赛道 = 新增一个 Source 子类并注册，其余（回测/分析/报告）全部自动可用。
"""

from __future__ import annotations

import os
import random
import re
import threading
import time
from abc import ABC, abstractmethod

import pandas as pd
import requests

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# 对公开接口保持克制：默认每次请求间隔 >= 3 秒。请勿调低。
MIN_GAP = float(os.environ.get("DCA_MIN_GAP", "3.0"))

_lock = threading.Lock()
_last = [0.0]
_sess = requests.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})


def throttle():
    with _lock:
        dt = time.time() - _last[0]
        if dt < MIN_GAP:
            time.sleep(MIN_GAP - dt + random.uniform(0, 0.5))
        _last[0] = time.time()


def http_get(url: str, referer: str | None = None, tries: int = 4, timeout: int = 30) -> str:
    last = None
    for i in range(tries):
        throttle()
        try:
            h = {"Referer": referer} if referer else {}
            r = _sess.get(url, headers=h, timeout=timeout)
            if r.status_code == 200 and r.content:
                return r.text
            last = f"HTTP {r.status_code} len={len(r.content)}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(3.0 * (i + 1) + random.uniform(0, 2.0))
    raise RuntimeError(f"GET failed after {tries} tries: {url} :: {last}")


class Source(ABC):
    """一个数据源。子类实现 _fetch()，返回 DataFrame[date, px]。

    px 必须是"可直接用于收益率计算"的序列：
      · 基金 -> 复权净值   · 指数 -> 全收益点位（没有则价格点位，需在配置里给 dividend）
      · 期货 -> 主力连续收盘价
    """

    key: str = ""
    label: str = ""
    #: 该源的数据是否已含分红再投资
    total_return: bool = False

    def __init__(self, cache_dir: str = "data"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _path(self, code: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{self.key}_{code}")
        return os.path.join(self.cache_dir, safe + ".parquet")

    def get(self, code: str, force: bool = False) -> pd.DataFrame:
        """带缓存的取数。返回 DataFrame[date, px]，按 date 升序。"""
        p = self._path(code)
        if os.path.exists(p) and not force:
            try:
                return self._clean(pd.read_parquet(p))
            except Exception:
                pass
        df = self._clean(self._fetch(code))
        if df.empty:
            raise RuntimeError(f"{self.key}:{code} returned no rows")
        df.to_parquet(p, index=False)
        return df

    @staticmethod
    def _clean(df: pd.DataFrame) -> pd.DataFrame:
        """统一清洗：去空、排序、剔除与主序列脱节的早期基期占位点。"""
        df = df.dropna().sort_values("date").reset_index(drop=True)
        if len(df) > 2:
            gap = df["date"].diff().dt.days
            # 头部若存在 > 1 年的断档，视为基期占位，丢弃断档之前的行
            head = gap[1 : min(6, len(df))]
            big = head[head > 365]
            if not big.empty:
                df = df.iloc[big.index[-1] :].reset_index(drop=True)
        return df

    @abstractmethod
    def _fetch(self, code: str) -> pd.DataFrame: ...

    def meta(self, code: str) -> dict:
        """可选：费率、名称、规模等。默认空。"""
        return {}


_REGISTRY: dict[str, type[Source]] = {}


def register(cls: type[Source]) -> type[Source]:
    _REGISTRY[cls.key] = cls
    return cls


def get_source(key: str, cache_dir: str = "data") -> Source:
    if key not in _REGISTRY:
        raise KeyError(f"未知数据源 '{key}'，可用: {sorted(_REGISTRY)}")
    return _REGISTRY[key](cache_dir=cache_dir)


def available() -> dict[str, str]:
    return {k: v.label for k, v in sorted(_REGISTRY.items())}
