"""组合定义：从 YAML/dict 描述一篮子资产，负责取数、对齐、口径校正。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .sources import get_source


@dataclass
class Asset:
    name: str
    source: str
    code: str
    weight: float = 0.0
    #: 价格指数缺失的年化股息率（小数）。数据源已含分红时留 0
    dividend: float = 0.0
    #: 模拟基金年费（小数）。数据本身已扣费（如 fund 源）时留 0
    annual_fee: float = 0.0
    #: 年化跟踪差（小数），从代理资产折算到可买产品时使用，正数表示扣减
    tracking_diff: float = 0.0
    #: 若资产以外币计价，填 'USDCNY' 之类，将换算为人民币
    fx: str | None = None
    note: str = ""
    #: 长历史代理：{source, code, dividend, annual_fee, tracking_diff, fx}
    #: 实盘买 code 指定的产品，回测用 proxy 拿更长的历史。二者应跟踪同一标的。
    proxy: dict | None = None

    def as_proxy(self) -> Asset:
        """返回用代理参数构造的等价 Asset。无 proxy 时返回自身。"""
        if not self.proxy:
            return self
        return Asset(
            name=self.name, weight=self.weight, note=self.note,
            source=self.proxy["source"], code=self.proxy["code"],
            dividend=self.proxy.get("dividend", 0.0),
            annual_fee=self.proxy.get("annual_fee", 0.0),
            tracking_diff=self.proxy.get("tracking_diff", 0.0),
            fx=self.proxy.get("fx"),
        )

    @property
    def gross_drag(self) -> float:
        return self.annual_fee + self.tracking_diff


def _fx_series(pair: str, cache_dir: str) -> pd.Series:
    """人民币汇率中间价。目前支持 USDCNY / EURCNY / JPYCNY / HKDCNY。"""
    import akshare as ak
    p = os.path.join(cache_dir, f"fx_{pair}.parquet")
    if os.path.exists(p):
        d = pd.read_parquet(p)
    else:
        d = ak.currency_boc_safe()
        d.to_parquet(p, index=False)
    col = {"USDCNY": "美元", "EURCNY": "欧元", "JPYCNY": "日元", "HKDCNY": "港元"}[pair.upper()]
    s = pd.Series(pd.to_numeric(d[col], errors="coerce").values,
                  index=pd.to_datetime(d["日期"])).dropna().sort_index() / 100.0
    return s


@dataclass
class Portfolio:
    name: str
    assets: list[Asset]
    monthly_amount: float = 1000.0
    buy_fee: float = 0.0012
    cache_dir: str = "data"
    meta: dict = field(default_factory=dict)

    # ---------- 构造 ----------
    @classmethod
    def from_dict(cls, cfg: dict, cache_dir: str = "data") -> Portfolio:
        assets = [Asset(**a) for a in cfg["assets"]]
        tw = sum(a.weight for a in assets)
        if tw <= 0:
            for a in assets:
                a.weight = 1.0 / len(assets)
        elif abs(tw - 1.0) > 1e-6:
            for a in assets:
                a.weight /= tw
        return cls(name=cfg.get("name", "portfolio"), assets=assets,
                   monthly_amount=float(cfg.get("monthly_amount", 1000)),
                   buy_fee=float(cfg.get("buy_fee", 0.0012)),
                   cache_dir=cache_dir,
                   meta={k: v for k, v in cfg.items() if k not in ("assets",)})

    @classmethod
    def from_yaml(cls, path: str, cache_dir: str = "data") -> Portfolio:
        import yaml
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(yaml.safe_load(f), cache_dir=cache_dir)

    # ---------- 取数 ----------
    def resolved(self, use_proxy: bool = False) -> list[Asset]:
        return [a.as_proxy() for a in self.assets] if use_proxy else self.assets

    def fetch(self, force: bool = False, verbose: bool = True, use_proxy: bool = False) -> dict[str, pd.DataFrame]:
        out = {}
        for a in self.resolved(use_proxy):
            src = get_source(a.source, self.cache_dir)
            df = src.get(a.code, force=force)
            out[a.name] = df
            if verbose:
                yrs = (df["date"].max() - df["date"].min()).days / 365.25
                print(f"  {a.name:16s} {a.source:9s} {a.code:<28s} "
                      f"{len(df):6d} 行  {df['date'].min().date()} ~ {df['date'].max().date()}  {yrs:5.1f}y")
        return out

    # ---------- 对齐 ----------
    def monthly(self, force: bool = False, verbose: bool = False,
                use_proxy: bool = False) -> pd.DataFrame:
        """月末价格矩阵，已做股息补偿与汇率换算（未扣费，费用在收益率层扣）。"""
        raw = self.fetch(force=force, verbose=verbose, use_proxy=use_proxy)
        cols = {}
        for a in self.resolved(use_proxy):
            s = (raw[a.name].set_index("date")["px"].sort_index().resample("ME").last().dropna())
            if a.fx:
                fx = _fx_series(a.fx, self.cache_dir).resample("ME").last()
                s = (s * fx.reindex(s.index).ffill()).dropna()
            if a.dividend:
                s = s * (1 + a.dividend) ** (np.arange(len(s)) / 12.0)
            cols[a.name] = s
        return pd.DataFrame(cols)

    def returns(self, start: str | None = None, end: str | None = None,
                dropna: bool = True, force: bool = False,
                use_proxy: bool = False) -> pd.DataFrame:
        """月度收益率矩阵，已扣模拟年费与跟踪差。

        use_proxy=True 时改用各资产的长历史代理（若配置了 proxy），
        用于在样本充足的窗口上做检验；实盘仍买 code 指定的产品。
        """
        px = self.monthly(force=force, use_proxy=use_proxy)
        if dropna:
            px = px.dropna()
        if start:
            px = px[px.index >= start]
        if end:
            px = px[px.index <= end]
        r = px.pct_change().dropna()
        amap = {a.name: a for a in self.resolved(use_proxy)}
        drag = np.array([amap[c].gross_drag for c in r.columns]) / 12.0
        return r - drag

    # ---------- 便捷 ----------
    def has_proxy(self) -> bool:
        return any(a.proxy for a in self.assets)

    def asset(self, name: str, use_proxy: bool = False) -> Asset:
        for a in self.resolved(use_proxy):
            if a.name == name:
                return a
        raise KeyError(name)

    @property
    def weights(self) -> pd.Series:
        return pd.Series({a.name: a.weight for a in self.assets})

    def blend(self, r: pd.DataFrame | None = None, weights: pd.Series | np.ndarray | None = None) -> pd.Series:
        """把收益率矩阵按权重合成单一序列。"""
        if r is None:
            r = self.returns()
        w = self.weights if weights is None else weights
        if isinstance(w, pd.Series):
            w = w.reindex(r.columns).values
        w = np.asarray(w, dtype=float)
        return (r * (w / w.sum())).sum(axis=1)

    def weighted_fee(self, use_proxy: bool = False) -> float:
        return float(sum(a.weight * a.gross_drag for a in self.resolved(use_proxy)))

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "资产": a.name, "源": a.source, "代码": a.code,
            "权重": a.weight, "年费/拖累": a.gross_drag,
            "股息补偿": a.dividend, "汇率": a.fx or "", "备注": a.note
        } for a in self.assets])
