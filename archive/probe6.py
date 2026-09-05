import warnings; warnings.filterwarnings("ignore")
import akshare as ak
def t(n,f):
    try:
        d=f(); print(f"[OK] {n}: rows={len(d)} cols={list(d.columns)[:6]}")
        print("   head:",dict(list(d.iloc[0].items())[:4])); print("   tail:",dict(list(d.iloc[-1].items())[:4]))
    except Exception as e: print(f"[FAIL] {n}: {type(e).__name__} {str(e)[:90]}")
t("上海金交所Au99.99 spot_hist_sge", lambda: ak.spot_hist_sge(symbol="Au99.99"))
t("人民币汇率中间价 currency_boc", lambda: ak.currency_boc_safe())
t("恒生指数 em", lambda: ak.stock_hk_index_daily_em(symbol="HSI"))
t("国际金价 futures", lambda: ak.futures_foreign_hist(symbol="GC"))
t("中债/国债收益率", lambda: ak.bond_zh_us_rate())
