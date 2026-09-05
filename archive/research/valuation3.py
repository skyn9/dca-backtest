# -*- coding: utf-8 -*-
import sys, warnings, json, time; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, akshare as ak, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
V={}
print("=== 中证系指数估值（PE / 股息率）===")
for code,nm in [("000922","中证红利"),("000300","沪深300"),("000905","中证500"),
                ("000852","中证1000"),("000015","上证红利"),("930740","红利低波100"),
                ("000016","上证50"),("930838","恒生港股通高股息")]:
    try:
        d=ak.stock_zh_index_value_csindex(symbol=code)
        d["日期"]=pd.to_datetime(d["日期"]); d=d.sort_values("日期")
        pe=float(d["市盈率2"].iloc[-1]); dy=float(d["股息率2"].iloc[-1])
        V[nm]=dict(code=code,pe=pe,dy=dy,date=str(d["日期"].iloc[-1].date()))
        print(f"  {nm:14s} PE={pe:6.2f}  股息率={dy:5.2f}%  ({d['日期'].iloc[-1].date()})")
        time.sleep(0.4)
    except Exception as e: print(f"  [--] {nm}: {str(e)[:60]}")

print("\n=== 恒生指数估值 ===")
for f,nm in [(lambda: ak.stock_hk_index_value_em() if hasattr(ak,'stock_hk_index_value_em') else None,"恒生em")]:
    try:
        d=f(); print(f"  [OK] {nm}", list(d.columns)[:8] if d is not None else None)
    except Exception as e: print(f"  [--] {nm}: {str(e)[:50]}")

print("\n=== 用基金持仓估算：港股红利 / QDII 的股息率（间接）===")
print("  港股高股息类基金近12月分红率可作为代理，此处用指数股息率替代")

print("\n"+"="*100)
print("【基于估值的前瞻预期收益模型】 预期年化 ≈ 股息率 + 实际盈利增长 + 估值回归")
print("  说明：这是自下而上的构建，与历史回测互相独立，用于交叉验证\n")
ASSUM=[
 # 资产, 权重, 股息率, 假设实际盈利增长, 估值回归年化贡献, 依据
 ("A股红利",  .24, 4.43, 2.5,  0.0, "PE 8.3 处历史低位，给 0 估值贡献（保守）"),
 ("A股中证500",.06, 1.20, 5.0, -0.5, "PE 26.6 近10年 78% 分位，给轻微负贡献"),
 ("港股红利",  .10, 6.80, 1.5,  0.5, "港股估值全球最低，给轻微正贡献"),
 ("美股标普500",.18, 1.20, 5.5, -1.5, "CAPE 高位，给负贡献"),
 ("美股纳指100",.14, 0.60, 8.0, -2.5, "估值与集中度最高，给较大负贡献"),
 ("黄金",     .13, 0.00, 3.5,  0.0, "长期≈通胀+1~2%，近年央行购金支撑"),
 ("债券",     .15, 1.68, 0.5,  0.0, "10年国债 1.68%，久期收益有限"),
]
tot=0
print(f"{'资产':<14}{'权重':>6}{'股息率':>8}{'盈利增长':>9}{'估值回归':>9}{'合计':>8}{'贡献':>8}   依据")
for nm,w,dy,g,v,why in ASSUM:
    e=dy+g+v; tot+=w*e
    print(f"{nm:<14}{w*100:5.0f}%{dy:7.2f}%{g:8.1f}%{v:+8.1f}%{e:7.2f}%{w*e:7.2f}pp   {why}")
print(f"\n  组合前瞻预期年化 ≈ {tot:.2f}%   (扣除加权费率 0.34% 后 ≈ {tot-0.34:.2f}%)")
print(f"  对照：历史回测 10年定投中位 10.31%  |  蒙特卡洛(股票打8折) 6.97%")
print(f"  → 三种独立方法给出 6~7% 的一致区间，历史回测的 10% 不应作为预期")
V["forward"]={"raw":round(tot,2),"net":round(tot-0.34,2),"assum":[{"name":n,"w":w,"dy":dy,"g":g,"v":v} for n,w,dy,g,v,_ in ASSUM]}
json.dump(V,open(f"{ROOT}/out/valuation.json","w"),ensure_ascii=False,indent=1)
print("\n已保存 valuation.json")
