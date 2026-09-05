import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import akshare as ak, pandas as pd
def t(n,f):
    try:
        d=f()
        print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:7]}")
        print("   head:",d.iloc[0].to_dict()); print("   tail:",d.iloc[-1].to_dict())
    except Exception as e: print(f"[FAIL] {n}: {type(e).__name__} {str(e)[:100]}")
t("index_us_stock_sina .INX", lambda: ak.index_us_stock_sina(symbol=".INX"))
t("index_us_stock_sina .IXIC", lambda: ak.index_us_stock_sina(symbol=".IXIC"))
t("index_us_stock_sina .NDX", lambda: ak.index_us_stock_sina(symbol=".NDX"))
t("stock_hk_index_daily_sina HSI", lambda: ak.stock_hk_index_daily_sina(symbol="HSI"))
t("macro_bank_usa? / 黄金 spot", lambda: ak.macro_cons_gold())
