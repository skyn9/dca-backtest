# -*- coding: utf-8 -*-
"""全维度矩阵：每个起投年 × 每个持有期限 的定投结果"""
import sys, json; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, dca_engine as E
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index2.parquet")
n=np.arange(len(A)); A["港股红利TR"]=A["港股红利"]*(1.04)**(n/12.0)
A["黄金AU0"]=pd.read_parquet(f"{ROOT}/data/gold_au0.parquet")["px"]
AS=["A股红利","A股中证500","港股红利TR","美股标普500(人民币)","美股纳斯达克(人民币)","黄金AU0","债券中证全债"]
FEE={"A股红利":.0020,"A股中证500":.0020,"港股红利TR":.0060,"美股标普500(人民币)":.0065,
     "美股纳斯达克(人民币)":.0065,"黄金AU0":.0030,"债券中证全债":.0030,"A股沪深300":.0020}
PLAN=np.array([.24,.06,.10,.18,.14,.13,.15])
M=A[AS+["A股沪深300"]].dropna()
R=M[AS].pct_change().dropna()-np.array([FEE[c] for c in AS])/12.0
RH=M["A股沪深300"].pct_change().dropna()-FEE["A股沪深300"]/12
prP=(R*PLAN).sum(axis=1)

def irr_from(pr, s, H, buy=0.0012):
    v=np.concatenate([[1.0],np.cumprod(1+pr.values[s:s+H])])
    if len(v)<H+1: return None
    units=sum(1000*(1-buy)/v[t] for t in range(H))
    return E.xirr_monthly([1000.0]*H, units*v[H])

YEARS=list(range(2008,2023)); HOR=[1,2,3,5,7,10,15]
idx=prP.index
out={"years":YEARS,"hor":HOR,"port":[],"hs":[]}
print("【全维度矩阵】每个起投年(1月) × 持有期限 的定投年化 IRR\n")
for tag,pr,store in [("★本方案",prP,"port"),("全仓沪深300",RH,"hs")]:
    print(f"--- {tag} ---")
    print("起投年 " + "".join(f"{h:>7}年" for h in HOR))
    for y in YEARS:
        cand=[i for i,d in enumerate(idx) if d.year==y and d.month==1]
        if not cand: out[store].append([None]*len(HOR)); continue
        s=cand[0]; row=[]
        line=f"{y}   "
        for H in HOR:
            H*=12
            if s+H>=len(pr): row.append(None); line+=f"{'—':>8}"; continue
            r=irr_from(pr,s,H); row.append(round(float(r),4) if r==r else None)
            line+=f"{r*100:7.1f}%"
        out[store].append(row); print(line)
    print()

# 汇总统计
print("="*90); print("【按期限汇总】所有起投年的分布")
print(f"{'期限':<6}{'方案':<12}{'最好':>9}{'中位':>9}{'最差':>9}{'亏损年数':>10}{'样本':>7}")
for j,h in enumerate(HOR):
    for tag,store in [("★本方案","port"),("沪深300","hs")]:
        v=[r[j] for r in out[store] if r[j] is not None]
        if not v: continue
        v=np.array(v)
        print(f"{h:<3}年  {tag:<12}{v.max()*100:8.2f}%{np.median(v)*100:8.2f}%{v.min()*100:8.2f}%{int((v<0).sum()):>7}/{len(v):<3}{len(v):>7}")
    print()
json.dump(out,open(f"{ROOT}/out/matrix.json","w"),ensure_ascii=False)
print("已保存 matrix.json")
