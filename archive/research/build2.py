# -*- coding: utf-8 -*-
"""扩充长窗口：加入港股红利(恒生港股通高股息 930838)，并生成最终分析数据集"""
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, numpy as np, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
A=pd.read_parquet(f"{ROOT}/data/monthly_index.parquet")
d=fetch.csindex("930838"); d=d[d["date"]>="2004-12-01"]
s=d.set_index("date")["px"].resample("ME").last()
A["港股红利"]=s
# 港股红利是价格指数? 校验：恒生高股息股息率高，加回 5.0%/y 作为全收益近似(保守取5%)
n=np.arange(len(A))
A["港股红利(全收益近似)"]=A["港股红利"]*(1.050)**(n/12.0)
A=A.dropna()
A.to_parquet(f"{ROOT}/data/monthly_index2.parquet")
print("长窗口2:",A.shape, A.index.min().date(),"~",A.index.max().date())
for c in A.columns:
    s=A[c].dropna(); yrs=len(s)/12; print(f"  {c:24s} CAGR={((s.iloc[-1]/s.iloc[0])**(1/yrs)-1)*100:6.2f}%")
