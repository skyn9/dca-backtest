# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import fetch, pandas as pd
CAND = [
 # A股宽基
 ("110020","易方达沪深300ETF联接A"),("000051","华夏沪深300ETF联接A"),
 ("000961","天弘沪深300ETF联接A"),("001052","华夏中证500ETF联接A"),
 ("000478","建信中证500增强A"),("161017","富国中证500指数A"),
 ("100032","富国中证红利指数增强A"),("008114","天弘中证红利低波100A"),
 ("110003","易方达上证50增强"),("161005","富国天惠成长A"),
 # 港股
 ("000071","华夏恒生ETF联接A"),("110031","易方达恒生H股ETF联接A"),
 ("013402","华夏恒生科技ETF联接A"),("501021","华宝香港中小"),
 # 美股 QDII
 ("050025","博时标普500ETF联接A"),("270042","广发纳斯达克100ETF联接A"),
 ("160213","国泰纳斯达克100"),("161125","易方达标普500(QDII-LOF)A"),
 ("161128","易方达标普信息科技A"),("040046","华安纳斯达克100A"),
 # 黄金/商品
 ("000216","华安黄金易ETF联接A"),("000307","易方达黄金ETF联接A"),
 # 债券
 ("110017","易方达增强回报A"),("217022","招商产业债A"),("000118","广发聚鑫A"),
 ("100018","富国天利增长债券"),("519977","长信可转债A"),
 # 其他市场
 ("000614","华安德国30(DAX)ETF联接"),("164824","工银印度市场"),
 ("161815","银华抗通胀(全球商品)"),
]
rows=[]
for code,name in CAND:
    try:
        df, meta = fetch.fund_hist(code)
        yrs = (df['date'].max()-df['date'].min()).days/365.25
        tot = df['adj'].iloc[-1]/df['adj'].iloc[0]
        cagr = tot**(1/yrs)-1 if yrs>0 else 0
        rows.append(dict(code=code,name=name,n=len(df),start=df['date'].min().date(),
                         end=df['date'].max().date(),yrs=round(yrs,1),cagr=round(cagr*100,2),
                         rate=meta.get('fund_Rate'),src_rate=meta.get('fund_sourceRate')))
        print(f"[OK] {code} {name[:22]:24s} {len(df):5d}行 {df['date'].min().date()}~{df['date'].max().date()} {yrs:4.1f}y CAGR={cagr*100:6.2f}% 费率{meta.get('fund_Rate')}")
    except Exception as e:
        print(f"[FAIL] {code} {name}: {type(e).__name__} {str(e)[:70]}")
pd.DataFrame(rows).to_csv("/Users/sky/PycharmProjects/DCA/data/fund_probe.csv",index=False)
