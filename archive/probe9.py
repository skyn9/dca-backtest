import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import akshare as ak, fetch, pandas as pd, json, re
def t(n,f):
    try:
        d=f(); print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:6]} head={dict(list(d.iloc[0].items())[:3])} tail={dict(list(d.iloc[-1].items())[:3])}")
        return d
    except Exception as e: print(f"[FAIL] {n}: {type(e).__name__} {str(e)[:80]}"); return None
t("现货黄金伦敦 spot", lambda: ak.spot_golden_benchmark_sge())
t("macro_cons_gold_amount", lambda: ak.macro_cons_gold_amount())
t("英为财情黄金? futures_global", lambda: ak.futures_global_hist_em(symbol="XAUUSD"))
t("外汇黄金 fx_quote", lambda: ak.fx_quote_baidu(symbol="黄金"))
# 新浪历史行情 hf 期货
for s in ["GC","XAU","AU"]:
    t(f"sina hf_{s}", lambda x=s: ak.futures_hq_daily_sina(symbol=x) if hasattr(ak,'futures_hq_daily_sina') else None)
