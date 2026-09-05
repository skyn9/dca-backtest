# -*- coding: utf-8 -*-
import sys, warnings, json; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch, akshare as ak
ROOT="/Users/sky/PycharmProjects/DCA"
def t(n,f):
    try:
        d=f(); print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:8]}"); print(d.tail(2).to_string()[:400]); return d
    except Exception as e: print(f"[--] {n}: {type(e).__name__} {str(e)[:70]}"); return None
print("=== A股估值 ===")
t("中证指数估值(csindex限流?)", lambda: fetch.csindex("H00922").tail(3))
t("A股主要指数市盈率 legu", lambda: ak.stock_market_pe_lg(symbol="沪深300"))
t("指数估值 lg", lambda: ak.stock_index_pe_lg(symbol="沪深300"))
t("A股整体PE lg", lambda: ak.stock_a_ttm_lyr())
t("A股股息率 lg", lambda: ak.stock_a_gxl_lg(symbol="沪深300"))
t("国债收益率", lambda: ak.bond_zh_us_rate().tail(3))
print("\n=== 美股估值 ===")
t("标普500 PE (lg)", lambda: ak.stock_us_pe_lg(symbol="标普500") if hasattr(ak,'stock_us_pe_lg') else None)
t("buffett指标", lambda: ak.stock_buffett_index_lg())
