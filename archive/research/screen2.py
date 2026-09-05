# -*- coding: utf-8 -*-
"""全市场筛选：每个目标指数下，抓取候选基金的费率+规模+净值，选出最优。"""
import sys, os, json, re, time, traceback
sys.path.insert(0, "/Users/sky/PycharmProjects/DCA/src")
import pandas as pd, fetch
ROOT = "/Users/sky/PycharmProjects/DCA"

allf = pd.read_csv(f"{ROOT}/data/all_funds.csv", dtype={"基金代码": str})
allf["name"] = allf["基金简称"]; allf["code"] = allf["基金代码"]; allf["type"] = allf["基金类型"]

# (key, 名称必须匹配, 排除, 允许的基金类型正则)
T = [
 ("hs300",  r"沪深300",            r"增强|量化|成长|价值|自由现金流|安中|等权|非银|医药|地产|消费|红利|波动|ESG|行业|信息|结构", r"指数型-股票"),
 ("a500",   r"中证A500",           r"增强|量化|自由现金流|质量|价值|成长|低波|ESG",                                      r"指数型-股票"),
 ("csi500", r"中证500",            r"增强|量化|质量|成长|价值|信息技术|医药|行业|等权|低波|ESG|低碳",                        r"指数型-股票"),
 ("csi1000",r"中证1000",           r"增强|量化|价值|成长|质量|ESG",                                                r"指数型-股票"),
 ("div",    r"中证红利|上证红利|红利低波|标普中国A股红利", r"增强|量化|质量|价值ETF|港股|恒生|港股通|全球|海外",                    r"指数型-股票"),
 ("gem",    r"创业板指|创业板50|创业板ETF联接", r"增强|量化|新能源|成长|低波|ESG",                                        r"指数型-股票"),
 ("star50", r"科创50|科创板50",       r"增强|量化|成长|ESG",                                                       r"指数型-股票"),
 ("hsi",    r"恒生指数|恒生ETF联接|沪港通恒生",  r"增强|科技|国企|医药|消费|红利|互联|中小|高股息",                              r"指数型"),
 ("hstech", r"恒生科技|恒生互联网|中国互联网|中概互联", r"增强|量化",                                                    r"指数型|QDII"),
 ("hsdiv",  r"恒生(高股息|红利)|港股(通)?(高股息|红利)|恒生红利低波", r"增强|量化",                                        r"指数型"),
 ("sp500",  r"标普500",             r"增强|信息科技|生物|医疗|消费|等权|质量|ESG|成长|价值",                              r"指数型|QDII"),
 ("ndx100", r"纳斯达克100|纳指100",    r"增强|生物|等权|ETF$",                                                     r"指数型|QDII"),
 ("dax",    r"德国30|德国DAX|德国ETF",  r"增强",                                                                r"指数型|QDII"),
 ("n225",   r"日经225|日本东证|日经ETF",  r"增强",                                                                r"指数型|QDII"),
 ("india",  r"印度",                r"增强",                                                                  r"指数型|QDII"),
 ("gold",   r"黄金ETF联接|上海金ETF联接|黄金基金", r"增强|股票|股|矿业",                                                r"指数型|QDII|商品"),
 ("bond",   r"", r"", r""),  # 债券单独处理
]
MAXN = 9
rows = []
for key, pat, exc, tpat in T:
    if key == "bond": continue
    m = allf[allf["name"].str.contains(pat, regex=True, na=False)]
    if tpat: m = m[m["type"].str.contains(tpat, regex=True, na=False)]
    if exc:  m = m[~m["name"].str.contains(exc, regex=True, na=False)]
    # 只要 A 类 / 无份额后缀
    m = m[~m["name"].str.contains(r"[CEIDYZ]$|C类|\(C\)|后端|美元|现汇|现钞|人民币C", regex=True, na=False)]
    m = m.drop_duplicates(subset=["code"]).head(40)
    print(f"\n=== {key}: 候选 {len(m)} 只，取前 {min(MAXN,len(m))} 抓详情")
    cnt = 0
    for _, r in m.iterrows():
        if cnt >= MAXN: break
        try:
            fee = fetch.fund_fees(r["code"])
            df, meta = fetch.fund_hist(r["code"])
            yrs = (df["date"].max() - df["date"].min()).days / 365.25
            sc = meta.get("scale_series") or []
            scale = sc[-1][1] if sc else None
            rows.append(dict(target=key, code=r["code"], name=r["name"], type=r["type"],
                             mgmt=fee["mgmt"], cust=fee["cust"], sales=fee["sales"],
                             annual=fee["total_annual"], buy=fee["buy_disc"],
                             yrs=round(yrs,1), start=str(df["date"].min().date()), scale=scale))
            print(f"  {r['code']} {r['name'][:26]:28s} 年费{fee['total_annual']:.2f}% 申购{fee['buy_disc']}% {yrs:4.1f}y 规模{scale}亿")
            cnt += 1
        except Exception as e:
            print(f"  [skip] {r['code']} {r['name'][:24]}: {type(e).__name__} {str(e)[:50]}")
pd.DataFrame(rows).to_csv(f"{ROOT}/data/screen_detail.csv", index=False)
print("\n保存", len(rows))
