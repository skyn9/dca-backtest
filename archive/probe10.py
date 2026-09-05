import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import fetch, pandas as pd
# 中证系列港股指数（全收益优先）
CODES=[("H30093","港股通高股息"),("930914","中证港股通高股息投资"),("H30533","港股通高股息全收益"),
       ("H11136","中证香港红利"),("930838","恒生港股通高股息"),("H30269","红利低波全收益"),
       ("H20269","红利低波100全收益"),("930740","中证红利低波动100"),("H00920","中证800全收益"),
       ("931052","中证A50"),("H30588","中证港股通综合全收益")]
for c,n in CODES:
    try:
        d=fetch.csindex(c); d=d[d['date']>'2000-01-01']
        yrs=(d['date'].max()-d['date'].min()).days/365.25
        cagr=(d['px'].iloc[-1]/d['px'].iloc[0])**(1/yrs)-1
        print(f"[OK] {c} {n:20s} {len(d):5d}行 {d['date'].min().date()}~{d['date'].max().date()} {yrs:5.1f}y CAGR={cagr*100:6.2f}%")
    except Exception as e:
        print(f"[--] {c} {n}: {str(e)[:50]}")
