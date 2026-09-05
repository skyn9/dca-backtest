# -*- coding: utf-8 -*-
import sys, warnings, json; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, akshare as ak, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
print("=== 各指数估值与历史分位（乐咕乐股）===")
OK={}
for sym in ["上证50","沪深300","中证500","中证1000","创业板指","科创50","上证指数","深证成指"]:
    try:
        d=ak.stock_index_pe_lg(symbol=sym)
        d["日期"]=pd.to_datetime(d["日期"])
        col="滚动市盈率" if "滚动市盈率" in d.columns else d.columns[-1]
        s=d.set_index("日期")[col].dropna()
        cur=s.iloc[-1]; q_all=(s<cur).mean(); s10=s[s.index>=s.index.max()-pd.Timedelta(days=3650)]
        q10=(s10<cur).mean()
        OK[sym]=dict(pe=float(cur),q_all=float(q_all),q10=float(q10),n=len(s),start=str(s.index.min().date()))
        print(f"  {sym:8s} PE-TTM={cur:6.2f}  全历史分位={q_all*100:5.1f}%  近10年分位={q10*100:5.1f}%  (自{s.index.min().date()}, {len(s)}点)")
    except Exception as e: print(f"  [--] {sym}: {str(e)[:60]}")

print("\n=== 股息率 ===")
for f,nm in [(lambda: ak.stock_a_gxl_lg(), "A股股息率(lg)")]:
    try:
        d=f(); print(f"  [OK] {nm}: cols={list(d.columns)[:8]}"); print("  ",d.tail(2).to_string()[:300])
    except Exception as e: print(f"  [--] {nm}: {str(e)[:70]}")
try:
    d=ak.stock_zh_index_value_csindex(symbol="000922")
    print(f"  [OK] 中证红利估值: cols={list(d.columns)}"); print("  ",d.tail(3).to_string()[:400])
except Exception as e: print(f"  [--] 中证红利估值: {str(e)[:70]}")

print("\n=== 美股/全球 ===")
for f,nm in [(lambda: ak.stock_buffett_index_lg(),"巴菲特指标(A股)"),
             (lambda: ak.index_us_stock_sina(symbol=".INX"),"标普500")]:
    try:
        d=f()
        if nm.startswith("巴"):
            d["r"]=d["总市值"]/d["GDP"]*100
            s=d.set_index(pd.to_datetime(d["日期"]))["r"].dropna()
            print(f"  A股总市值/GDP = {s.iloc[-1]:.1f}%  全历史分位={(s<s.iloc[-1]).mean()*100:.1f}%")
        else: print(f"  标普500 现值={d['close'].iloc[-1]:.0f}")
    except Exception as e: print(f"  [--] {nm}: {str(e)[:60]}")
json.dump(OK,open(f"{ROOT}/out/valuation.json","w"),ensure_ascii=False,indent=1)

print("\n=== 无风险利率（决定债券部分的前瞻预期）===")
b=ak.bond_zh_us_rate().dropna(subset=["中国国债收益率10年"])
b["日期"]=pd.to_datetime(b["日期"]); s=b.set_index("日期")["中国国债收益率10年"]
print(f"  中国10年国债 {s.iloc[-1]:.3f}%   历史均值={s.mean():.2f}%   全历史分位={(s<s.iloc[-1]).mean()*100:.1f}%")
print(f"  美国10年国债 {b['美国国债收益率10年'].iloc[-1]:.2f}%")
print(f"  中国30年国债 {b['中国国债收益率30年'].iloc[-1]:.3f}%")
