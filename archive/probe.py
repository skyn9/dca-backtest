import warnings, traceback
warnings.filterwarnings("ignore")
import akshare as ak
import pandas as pd

def t(name, fn):
    try:
        df = fn()
        if df is None or len(df)==0:
            print(f"[EMPTY] {name}")
            return
        print(f"[OK] {name}: rows={len(df)} cols={list(df.columns)[:8]}")
        print(f"       head={df.iloc[0].to_dict() if len(df) else ''}")
        print(f"       tail={df.iloc[-1].to_dict() if len(df) else ''}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {str(e)[:120]}")

print("=== akshare", ak.__version__)
t("A股指数-沪深300(em)", lambda: ak.index_zh_a_hist(symbol="000300", period="daily", start_date="20050101", end_date="20260905"))
t("A股指数-中证500(em)", lambda: ak.index_zh_a_hist(symbol="000905", period="daily", start_date="20050101", end_date="20260905"))
t("指数daily(sina)-沪深300", lambda: ak.stock_zh_index_daily(symbol="sh000300"))
t("指数daily(em)-沪深300", lambda: ak.stock_zh_index_daily_em(symbol="sh000300"))
