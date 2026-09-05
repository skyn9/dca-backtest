"""dca —— 定投组合回测与稳健性检验框架。

快速开始：
    from dca import Portfolio, analysis
    p = Portfolio.from_yaml("configs/default.yaml")
    r = p.returns()
    print(analysis.rolling_table(r, p.weights))
"""
from .portfolio import Portfolio, Asset
from . import engine, analysis, sources

__version__ = "0.1.0"
__all__ = ["Portfolio", "Asset", "engine", "analysis", "sources"]
