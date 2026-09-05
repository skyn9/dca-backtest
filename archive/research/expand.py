# -*- coding: utf-8 -*-
"""扩充资产宇宙：更多市场/品类，并为每类找长历史代理"""
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch, akshare as ak, json, re
ROOT="/Users/sky/PycharmProjects/DCA"

print("="*100); print("【1】中证/国证 更多指数（全收益优先）")
CS=[("H00922","中证红利全收益"),("H00300","沪深300全收益"),("H00905","中证500全收益"),
    ("H00852","中证1000全收益"),("H11001","中证全债"),("H00016","上证50全收益"),
    ("930838","恒生港股通高股息"),("H30093","港股通高股息"),("H11025","中证转债"),
    ("H30533","港股通高股息全收益"),("000827","中证环保"),("H20269","红利低波100全收益[已剔除]"),
    ("931052","中证A50"),("H00985","中证全指全收益"),("000015","上证红利"),
    ("H11136","中证香港红利"),("930914","中证港股通高股息投资"),("H30269","红利低波全收益")]
res={}
for c,nm in CS:
    try:
        d=fetch.csindex(c); d=d[d["date"]>"2000-01-01"]
        yy=(d["date"].max()-d["date"].min()).days/365.25
        cagr=(d["px"].iloc[-1]/d["px"].iloc[0])**(1/yy)-1
        res[c]=d; print(f"  [OK] {c:8s} {nm:22s} {len(d):5d}行 {d['date'].min().date()}~{d['date'].max().date()} {yy:5.1f}y CAGR={cagr*100:6.2f}%")
    except Exception as e: print(f"  [--] {c:8s} {nm:22s} {str(e)[:50]}")

print("\n"+"="*100); print("【2】新浪/期货 长历史（黄金已获，再找原油/其他商品与海外）")
SINA=[("AU0","沪金主力"),("AG0","沪银主力"),("CU0","沪铜主力"),("SC0","原油主力"),("RB0","螺纹主力")]
for s,nm in SINA:
    try:
        t=fetch.get(f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/x/InnerFuturesNewService.getDailyKLine?symbol={s}",
                    referer="https://finance.sina.com.cn/")
        js=json.loads(re.search(r"x\((\[.*\])\)",t,re.S).group(1))
        d=pd.DataFrame(js)[["d","c"]]; d["d"]=pd.to_datetime(d["d"]); d["c"]=pd.to_numeric(d["c"])
        yy=(d["d"].max()-d["d"].min()).days/365.25
        print(f"  [OK] {s:5s} {nm:8s} {len(d):5d}行 {d['d'].min().date()}~{d['d'].max().date()} {yy:5.1f}y CAGR={((d['c'].iloc[-1]/d['c'].iloc[0])**(1/yy)-1)*100:6.2f}%")
        d.rename(columns={"d":"date","c":"px"}).to_parquet(f"{ROOT}/data/fut_{s}.parquet",index=False)
    except Exception as e: print(f"  [--] {s:5s} {nm:8s} {str(e)[:60]}")

print("\n"+"="*100); print("【3】海外指数（新浪 长历史）")
US=[(".INX","标普500"),(".IXIC","纳斯达克综合"),(".DJI","道琼斯"),(".NDX","纳指100")]
for s,nm in US:
    try:
        d=ak.index_us_stock_sina(symbol=s)[["date","close"]]
        d["date"]=pd.to_datetime(d["date"]); yy=(d["date"].max()-d["date"].min()).days/365.25
        print(f"  [OK] {s:8s} {nm:10s} {len(d):5d}行 {d['date'].min().date()}~{d['date'].max().date()} {yy:5.1f}y CAGR={((d['close'].iloc[-1]/d['close'].iloc[0])**(1/yy)-1)*100:6.2f}%")
        d.rename(columns={"close":"px"}).to_parquet(f"{ROOT}/data/us_{s.strip('.')}.parquet",index=False)
    except Exception as e: print(f"  [--] {s} {nm}: {str(e)[:60]}")
for s,nm in [("HSI","恒生指数"),("HSCEI","恒生国企"),("HSTECH","恒生科技")]:
    try:
        d=ak.stock_hk_index_daily_sina(symbol=s)[["date","close"]]
        d["date"]=pd.to_datetime(d["date"]); yy=(d["date"].max()-d["date"].min()).days/365.25
        print(f"  [OK] {s:8s} {nm:10s} {len(d):5d}行 {d['date'].min().date()}~{d['date'].max().date()} {yy:5.1f}y")
        d.rename(columns={"close":"px"}).to_parquet(f"{ROOT}/data/hk_{s}.parquet",index=False)
    except Exception as e: print(f"  [--] {s} {nm}: {str(e)[:60]}")
