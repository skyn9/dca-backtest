import warnings; warnings.filterwarnings("ignore")
import akshare as ak
def t(n,f):
    try:
        d=f(); print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:12]}")
        print(d.head(3).to_string()[:600])
    except Exception as e: print(f"[FAIL] {n}: {type(e).__name__} {str(e)[:90]}")
t("全部基金名录 fund_name_em", lambda: ak.fund_name_em())
t("指数型排行 fund_open_fund_rank_em(指数型)", lambda: ak.fund_open_fund_rank_em(symbol="指数型"))
t("QDII排行", lambda: ak.fund_open_fund_rank_em(symbol="QDII"))
