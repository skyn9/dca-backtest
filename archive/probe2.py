# -*- coding: utf-8 -*-
import sys, traceback
sys.path.insert(0, "/Users/sky/PycharmProjects/DCA/src")
import fetch

def show(tag, fn):
    try:
        r = fn()
        df = r[0] if isinstance(r, tuple) else r
        print(f"[OK]   {tag:34s} n={len(df):5d}  {df['date'].min().date()} -> {df['date'].max().date()}")
    except Exception as e:
        print(f"[FAIL] {tag:34s} {type(e).__name__}: {str(e)[:90]}")

print("### 中证全收益指数（csindex 官网）")
for code, nm in [("H00300","沪深300全收益"),("H00905","中证500全收益"),("H00852","中证1000全收益"),
                 ("H00922","中证红利全收益"),("H00016","上证50全收益"),("H30269","红利低波全收益"),
                 ("H11001","中证全债"),("H00510","中证A500全收益"),("H20955","科创50全收益")]:
    show(f"csindex {code} {nm}", lambda c=code: fetch.csindex(c))

print("\n### 东财 K 线：A股/港股/美股/商品")
for sec, nm in [("1.000300","沪深300"),("1.000905","中证500"),("1.000852","中证1000"),
                ("0.399006","创业板指"),("1.000922","中证红利"),("1.000015","上证红利"),
                ("124.HSI","恒生指数"),("124.HSCEI","恒生国企"),("124.HSTECH","恒生科技"),
                ("100.NDX","纳斯达克100"),("100.SPX","标普500"),("100.DJIA","道琼斯"),
                ("100.N225","日经225"),("100.GDAXI","德国DAX"),("100.SENSEX","印度Sensex"),
                ("101.GC00Y","COMEX黄金"),("118.AU9999","上海金")]:
    show(f"em {sec} {nm}", lambda s=sec: fetch.em_kline(s))
