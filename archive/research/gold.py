# -*- coding: utf-8 -*-
"""抓沪金主力连续(AU0)，并与黄金ETF联接真实净值交叉验证"""
import sys, re, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
txt=fetch.get("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/x/InnerFuturesNewService.getDailyKLine?symbol=AU0",
              referer="https://finance.sina.com.cn/")
js=json.loads(re.search(r"x\((\[.*\])\)", txt, re.S).group(1))
g=pd.DataFrame(js)[["d","c"]].rename(columns={"d":"date","c":"px"})
g["date"]=pd.to_datetime(g["date"]); g["px"]=pd.to_numeric(g["px"])
g=g.sort_values("date").reset_index(drop=True)
gm=g.set_index("date")["px"].resample("ME").last()
print(f"沪金AU0: {len(g)}行 {g['date'].min().date()} ~ {g['date'].max().date()}  月度{len(gm)}点")
yrs=len(gm)/12; print(f"  期间CAGR={((gm.iloc[-1]/gm.iloc[0])**(1/yrs)-1)*100:.2f}%  ({yrs:.1f}年)")

# 与华安黄金ETF联接A(000216)真实净值交叉验证
f,_=fetch.fund_hist("000216")
fm=f.set_index("date")["adj"].resample("ME").last()
j=pd.concat([gm.rename("au0"), fm.rename("fund")],axis=1).dropna()
r=j.pct_change().dropna()
print(f"\n交叉验证 (重叠 {j.index.min().date()}~{j.index.max().date()}, {len(j)}月):")
print(f"  月度收益相关性 = {r['au0'].corr(r['fund']):.4f}")
ya=(j['au0'].iloc[-1]/j['au0'].iloc[0])**(12/(len(j)-1))-1
yf=(j['fund'].iloc[-1]/j['fund'].iloc[0])**(12/(len(j)-1))-1
print(f"  AU0年化={ya*100:.2f}%  基金年化={yf*100:.2f}%  差={(ya-yf)*100:+.2f}pp/年 (基金费率0.6%+跟踪误差)")
print(f"  年化跟踪差 -> 用 AU0 回测时应扣减 {(ya-yf)*100:.2f}% 以模拟真实基金")
gm.to_frame("px").to_parquet(f"{ROOT}/data/gold_au0.parquet")
print("\n已保存 gold_au0.parquet")
