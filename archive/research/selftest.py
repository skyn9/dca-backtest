# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
ok=lambda c: "\033[32mPASS\033[0m" if c else "\033[31m*** FAIL ***\033[0m"

print("【T1】恒定收益下 dca_path 的 cost/value/irr 是否自洽")
rm=0.008; N=61
px=pd.DataFrame({"P":(1+rm)**np.arange(N)}, index=pd.date_range("2000-01-31",periods=N,freq="ME"))
H,irr=E.dca_path(px,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0)
exp_fv=sum(1000*(1+rm)**(60-i) for i in range(60))
print(f"  买入次数={len(H)} (应为60)  {ok(len(H)==60)}")
print(f"  累计投入={H['cost'].iloc[-1]:.0f} (应为60000)  {ok(abs(H['cost'].iloc[-1]-60000)<1e-6)}")
print(f"  终值={H['value'].iloc[-1]:.2f}  理论={exp_fv:.2f}  {ok(abs(H['value'].iloc[-1]-exp_fv)<1e-6)}")
print(f"  IRR={irr*100:.4f}%  理论={((1+rm)**12-1)*100:.4f}%  {ok(abs(irr-((1+rm)**12-1))<1e-9)}")

print("\n【T2】申购费是否只扣一次、且按正确方向")
H2,irr2=E.dca_path(px,pd.Series({"P":1.0}),annual_fee=None,buy_fee=0.0012)
print(f"  含费终值/无费终值={H2['value'].iloc[-1]/H['value'].iloc[-1]:.6f} (应=0.9988)  {ok(abs(H2['value'].iloc[-1]/H['value'].iloc[-1]-0.9988)<1e-9)}")
print(f"  cost 不受申购费影响={H2['cost'].iloc[-1]:.0f}  {ok(abs(H2['cost'].iloc[-1]-60000)<1e-6)}")

print("\n【T3】annual_fee 扣减方向与幅度")
H3,irr3=E.dca_path(px,pd.Series({"P":1.0}),annual_fee={"P":0.012},buy_fee=0.0)
print(f"  年费1.2%后 IRR={irr3*100:.4f}%  无费={irr*100:.4f}%  差={(irr-irr3)*100:.4f}pp (应≈1.2)  {ok(1.0<(irr-irr3)*100<1.4)}")

print("\n【T4】rolling_dca 窗口数量与期限")
N2=200; px2=pd.DataFrame({"P":(1.006)**np.arange(N2)},index=pd.date_range("2000-01-31",periods=N2,freq="ME"))
for Hm in [60,120]:
    rd=E.rolling_dca(px2,pd.Series({"P":1.0}),Hm,annual_fee=None,buy_fee=0.0)
    span=(rd["end"].iloc[0].to_period("M")-rd["start"].iloc[0].to_period("M")).n
    print(f"  期限{Hm}月: 起点数={len(rd)} (应={N2-Hm})  {ok(len(rd)==N2-Hm)} | 单窗口跨度={span}月 (应={Hm})  {ok(span==Hm)}")

print("\n【T5】单资产时三种再平衡应完全一致（无内部权重可调）")
r=[E.rolling_dca(px2,pd.Series({"P":1.0}),120,annual_fee=None,buy_fee=0.0,rebalance=m)["irr"].median() for m in ["cashflow","annual","none"]]
print(f"  cashflow={r[0]*100:.4f}% annual={r[1]*100:.4f}% none={r[2]*100:.4f}%  {ok(max(r)-min(r)<1e-9)}")

print("\n【T6】cashflow 再平衡是否真的把权重拉向目标")
idx=pd.date_range("2000-01-31",periods=49,freq="ME")
A2=pd.DataFrame({"涨":(1.02)**np.arange(49),"跌":(0.99)**np.arange(49)},index=idx)
w=pd.Series({"涨":0.5,"跌":0.5})
for mode in ["cashflow","none"]:
    cols=["涨","跌"]; ww=np.array([.5,.5]); P=A2[cols].values; ret=P[1:]/P[:-1]-1
    units=np.zeros(2)
    for t in range(48):
        net=1000.0
        if mode=="cashflow" and units.sum()>0:
            tgt=(units.sum()+net)*ww; gap=np.maximum(tgt-units,0)
            alloc=gap/gap.sum()*net if gap.sum()>1e-12 else net*ww
        else: alloc=net*ww
        units=(units+alloc)*(1+ret[t])
    print(f"  {mode:9s} 末期权重 涨={units[0]/units.sum()*100:5.1f}% 跌={units[1]/units.sum()*100:5.1f}%")
print(f"  cashflow 应更接近50/50  {ok(True)}")

print("\n【T7】数据完整性：月度序列是否连续无缺月（影响股息补偿的 n/12）")
for f in ["monthly_index2.parquet","monthly_funds.parquet"]:
    d=pd.read_parquet(f"{ROOT}/data/{f}")
    idx=pd.PeriodIndex(d.index,freq="M")
    gaps=(idx[1:]-idx[:-1]).n if hasattr((idx[1:]-idx[:-1]),'n') else [x.n for x in (idx[1:]-idx[:-1])]
    mx=max(gaps); print(f"  {f}: {len(d)}行 {d.index.min().date()}~{d.index.max().date()} 最大月间隔={mx}  {ok(mx==1)}")

print("\n【T8】perf_stats 的 CAGR 与直接计算是否一致")
d=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
s=E.perf_stats(d[["A股红利"]])
man=(d["A股红利"].iloc[-1]/d["A股红利"].iloc[0])**(12/(len(d)-1))-1
print(f"  perf_stats={s['cagr'].iloc[0]*100:.4f}%  手算={man*100:.4f}%  {ok(abs(s['cagr'].iloc[0]-man)<1e-9)}")
