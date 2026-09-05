# -*- coding: utf-8 -*-
"""对每个目标指数，从全市场指数基金中筛选出费率最低/规模合格的场外基金。"""
import sys, os, json, re, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd, fetch

ROOT = "/Users/sky/PycharmProjects/DCA"
funds = pd.read_csv(f"{ROOT}/data/index_funds_em.csv", dtype={"基金代码": str})
allf = pd.read_csv(f"{ROOT}/data/all_funds.csv", dtype={"基金代码": str}) if os.path.exists(f"{ROOT}/data/all_funds.csv") else None

# 目标标的: (键, 名称正则-必须含, 排除正则)
TARGETS = [
 ("hs300",   r"沪深300|沪深３００",                       r"增强|指数增强|ETF联接\(QDII|[C]类$"),
 ("a500",    r"中证A500|中证A50\b",                      r"增强"),
 ("csi500",  r"中证500",                                r"增强|500ETF联接\(QDII"),
 ("csi1000", r"中证1000",                               r"增强"),
 ("div",     r"中证红利|红利低波|红利低波动|上证红利|标普中国A股红利",  r"增强|港股|恒生"),
 ("gem",     r"创业板指|创业板ETF联接|创业板50",              r"增强|新能源"),
 ("star50",  r"科创50|科创板50",                          r"增强"),
 ("hsi",     r"恒生指数|恒生ETF联接",                       r"增强|科技|国企|医药|消费|红利"),
 ("hstech",  r"恒生科技|恒生互联网|中国互联网",                 r"增强"),
 ("hsdiv",   r"恒生(高股息|红利)|港股(通)?(高股息|红利)",         r"增强"),
 ("sp500",   r"标普500",                                r"增强|信息科技|生物|医疗|消费"),
 ("ndx100",  r"纳斯达克100|纳指100|纳斯达克指数",              r"增强|生物"),
 ("dax",     r"德国30|德国DAX|德国ETF",                    r"增强"),
 ("n225",    r"日经225|日本东证|日经ETF",                    r"增强"),
 ("india",   r"印度",                                    r"增强"),
 ("gold",    r"黄金ETF联接|黄金基金|上海金ETF联接",             r"增强|股票|股"),
]

def pick(pat, exc):
    m = funds[funds["基金名称"].str.contains(pat, regex=True, na=False)]
    if exc:
        m = m[~m["基金名称"].str.contains(exc, regex=True, na=False)]
    return m

rows = []
for key, pat, exc in TARGETS:
    m = pick(pat, exc)
    # 只保留 A 类/无后缀（长期定投优选 A 类），排除 C/E/I/D/Y 类和联接C
    keep = m[~m["基金名称"].str.contains(r"[CEIDY]$|C类|联接C|\(C\)|H$", regex=True, na=False)]
    if len(keep) == 0: keep = m
    print(f"\n### {key}  匹配{len(m)}只 / A类{len(keep)}只")
    print(keep[["基金代码","基金名称","成立来","手续费"]].head(14).to_string(index=False))
    for _, r in keep.iterrows():
        rows.append(dict(target=key, code=r["基金代码"], name=r["基金名称"],
                         since_incept=r["成立来"], fee_str=r["手续费"]))
pd.DataFrame(rows).to_csv(f"{ROOT}/data/screen_candidates.csv", index=False)
print(f"\n候选合计 {len(rows)}")
