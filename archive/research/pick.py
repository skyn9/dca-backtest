# -*- coding: utf-8 -*-
"""最终选基：每类中选 年费率最低 + 规模>2亿 + 成立>1年 的场外A类"""
import sys, re; sys.path.insert(0,"/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, fetch
ROOT="/Users/sky/PycharmProjects/DCA"
d=pd.read_csv(f"{ROOT}/data/screen_detail.csv",dtype={"code":str})
def scale(x):
    try: return float(eval(x)["y"]) if isinstance(x,str) and "y" in x else None
    except: return None
d["scale_y"]=d["scale"].apply(scale)
d=d[~d["name"].str.contains(r"ETF$|^.*ETF[东南西北]?$",regex=True,na=False)]      # 去掉场内ETF
d=d[~d["code"].str.match(r"^(1[56]|51|58)\d{4}$")]                              # 去掉场内代码
ORDER=["hs300","a500","csi500","div","hsdiv","hstech","sp500","ndx100","gold","n225"]
NAME={"hs300":"A股沪深300","a500":"A股中证A500","csi500":"A股中证500","div":"A股红利",
      "hsdiv":"港股红利","hstech":"港股科技","sp500":"美股标普500","ndx100":"美股纳指100",
      "gold":"黄金","n225":"日经225"}
print(f"{'类别':<12}{'代码':<8}{'基金名称':<32}{'年费率':>7}{'申购费':>7}{'规模亿':>8}{'成立':>6}")
print("-"*88)
for t in ORDER:
    s=d[d["target"]==t].copy()
    s=s[(s["scale_y"].fillna(0)>=2.0)&(s["yrs"]>=1.0)]
    s=s.sort_values(["annual","scale_y"],ascending=[True,False])
    for _,r in s.head(3).iterrows():
        print(f"{NAME[t]:<12}{r['code']:<8}{str(r['name'])[:30]:<32}{r['annual']:>6.2f}%{str(r['buy']):>6}%{r['scale_y']:>7.1f}{r['yrs']:>5.1f}y")
    print()
