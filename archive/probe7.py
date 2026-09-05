import warnings; warnings.filterwarnings("ignore")
import akshare as ak, pandas as pd, requests, json, sys
sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src"); import fetch
def t(n,f):
    try:
        d=f(); print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:6]}  head={dict(list(d.iloc[0].items())[:3])} tail={dict(list(d.iloc[-1].items())[:3])}")
    except Exception as e: print(f"[FAIL] {n}: {type(e).__name__} {str(e)[:80]}")
t("sge 现货全部", lambda: ak.spot_symbol_table_sge())
t("Au(T+D)", lambda: ak.spot_hist_sge(symbol="Au(T+D)"))
t("伦敦金 macro_cons_gold_volume", lambda: ak.futures_global_hist_em(symbol="伦敦金"))
# 新浪伦敦金/外盘
for sym in ["hf_GC","hf_XAU"]:
    t(f"新浪外盘 {sym}", lambda s=sym: ak.futures_foreign_hist(symbol=s))
# 东财 通过基金：博时黄金ETF 159937 / 华安黄金ETF 518880
t("黄金ETF华安518880(em)", lambda: fetch.em_kline("1.518880"))
