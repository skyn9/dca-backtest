# -*- coding: utf-8 -*-
"""数据抓取层：东方财富 / 新浪 / 中证指数 / 天天基金，带本地缓存与重试。"""
import os, re, json, time, random, hashlib
import requests
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data")
os.makedirs(CACHE, exist_ok=True)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_SESS = requests.Session()
_SESS.headers.update({"User-Agent": UA, "Accept": "*/*",
                      "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
_LAST = [0.0]

def _throttle(min_gap=1.6):
    dt = time.time() - _LAST[0]
    if dt < min_gap:
        time.sleep(min_gap - dt + random.uniform(0, 0.35))
    _LAST[0] = time.time()

def get(url, referer=None, tries=4, timeout=25, text=True):
    last = None
    for i in range(tries):
        _throttle()
        try:
            h = {"Referer": referer} if referer else {}
            r = _SESS.get(url, headers=h, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 0:
                return r.text if text else r.content
            last = f"HTTP {r.status_code} len={len(r.content)}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2.5 * (i + 1) + random.uniform(0, 1.5))
    raise RuntimeError(f"GET failed after {tries}: {url} :: {last}")

def _cpath(key):
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".parquet")

def cached(key, builder, force=False):
    p = _cpath(key)
    if os.path.exists(p) and not force:
        try:
            return pd.read_parquet(p)
        except Exception:
            pass
    df = builder()
    if df is not None and len(df):
        df.to_parquet(p, index=False)
    return df

# ---------------- 东方财富 K 线 ----------------
def em_kline(secid, fqt=1):
    """secid 例: 1.000300(沪) 0.399006(深) 100.NDX(国际) 124.HSI(港) 133.xxx"""
    url = ("https://push2his.eastmoney.com/api/qt/stock/kline/get?"
           f"secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57"
           f"&klt=101&fqt={fqt}&beg=0&end=20500101&lmt=100000")
    js = json.loads(get(url, referer="https://quote.eastmoney.com/"))
    d = js.get("data") or {}
    kl = d.get("klines") or []
    if not kl:
        raise RuntimeError(f"empty klines for {secid}: {js.get('rc')}")
    rows = [x.split(",") for x in kl]
    df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume", "amount"][:len(rows[0])])
    df["date"] = pd.to_datetime(df["date"])
    for c in df.columns:
        if c != "date":
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df.attrs["name"] = d.get("name", "")
    return df[["date", "close"]].rename(columns={"close": "px"}).dropna()

def em_name(secid):
    url = (f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f58,f43")
    js = json.loads(get(url, referer="https://quote.eastmoney.com/"))
    return (js.get("data") or {}).get("f58")

# ---------------- 新浪指数 ----------------
def sina_index(symbol):
    """symbol 例: sh000300 sz399006"""
    url = f"https://finance.sina.com.cn/realstock/company/{symbol}/hisdata/klc_kl.js"
    txt = get(url, referer="https://finance.sina.com.cn/")
    m = re.findall(r'"day":"(\d{4}-\d{2}-\d{2})".*?"close":"([\d.]+)"', txt)
    if not m:
        raise RuntimeError("sina parse fail")
    df = pd.DataFrame(m, columns=["date", "px"])
    df["date"] = pd.to_datetime(df["date"]); df["px"] = pd.to_numeric(df["px"])
    return df.sort_values("date").reset_index(drop=True)

# ---------------- 中证指数官网（全收益指数） ----------------
def csindex(code, force=False):
    """code 例: H00300(沪深300全收益) H00905 H00922. 返回收盘点位。带本地缓存。"""
    return cached(f"csidx_{code}", lambda: _csindex_raw(code), force=force)

def _csindex_raw(code):
    url = ("https://www.csindex.com.cn/csindex-home/perf/index-perf"
           f"?indexCode={code}&startDate=19900101&endDate=20991231")
    txt = get(url, referer="https://www.csindex.com.cn/")
    js = json.loads(txt)
    data = js.get("data") or []
    if not data:
        raise RuntimeError(f"csindex empty {code}")
    df = pd.DataFrame(data)
    col = "tclose" if "tclose" in df.columns else "close"
    df = df[["tradeDate", col]].rename(columns={"tradeDate": "date", col: "px"})
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
    df["px"] = pd.to_numeric(df["px"], errors="coerce")
    return df.dropna().sort_values("date").reset_index(drop=True)

# ---------------- 天天基金全历史 ----------------
def fund_hist(code):
    """返回 date / nav(单位净值) / acc(累计净值) / ret(复权日收益%) / adj(复权净值)"""
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    s = get(url, referer=f"https://fund.eastmoney.com/{code}.html")
    def arr(name):
        m = re.search(rf"var\s+{name}\s*=\s*(\[.*?\]);", s, re.S)
        return json.loads(m.group(1)) if m else []
    nw = arr("Data_netWorthTrend")
    if not nw:
        raise RuntimeError(f"no nav for {code}")
    df = pd.DataFrame(nw)
    df["date"] = pd.to_datetime(df["x"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
    df = df.rename(columns={"y": "nav", "equityReturn": "ret"})[["date", "nav", "ret"]]
    ac = arr("Data_ACWorthTrend")
    if ac:
        a = pd.DataFrame(ac, columns=["x", "acc"])
        a["date"] = pd.to_datetime(a["x"], unit="ms", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize()
        df = df.merge(a[["date", "acc"]], on="date", how="left")
    else:
        df["acc"] = df["nav"]
    df["ret"] = pd.to_numeric(df["ret"], errors="coerce").fillna(0.0)
    df["adj"] = (1 + df["ret"] / 100.0).cumprod()
    meta = {}
    for k in ["fS_name", "fund_Rate", "fund_sourceRate", "fund_minsg", "syl_1n", "syl_3y", "syl_6y"]:
        m = re.search(rf'var\s+{k}\s*=\s*"?([^";]*)"?;', s)
        meta[k] = m.group(1) if m else None
    m = re.search(r"var\s+Data_fluctuationScale\s*=\s*(\{.*?\});", s, re.S)
    if m:
        try:
            fs = json.loads(m.group(1))
            meta["scale_series"] = list(zip(fs.get("categories", []), fs.get("series", [])))[-4:]
        except Exception:
            pass
    df.attrs["meta"] = meta
    return df.sort_values("date").reset_index(drop=True), meta

# ---------------- 基金费率（F10） ----------------
def fund_fees(code):
    """返回管理费/托管费/销售服务费(年%)与申购优惠费率(%)"""
    h = get(f"https://fundf10.eastmoney.com/jjfl_{code}.html",
            referer="https://fundf10.eastmoney.com/")
    t = re.sub(r"<[^>]+>", " ", h)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"\s+", " ", t)
    def pct(label):
        m = re.search(label + r"\s*([\d.]+)%", t)
        return float(m.group(1)) if m else None
    out = {"mgmt": pct("管理费率"), "cust": pct("托管费率"), "sales": pct("销售服务费率")}
    m = re.search(r"申购费率.*?小于100万元\s*([\d.]+)%\s*\|\s*([\d.]+)%", t)
    if m:
        out["buy_std"], out["buy_disc"] = float(m.group(1)), float(m.group(2))
    else:
        m2 = re.search(r"申购费率.*?小于100万元\s*([\d.]+)%", t)
        out["buy_std"] = float(m2.group(1)) if m2 else None
        out["buy_disc"] = out["buy_std"]
    out["total_annual"] = sum(v for v in [out["mgmt"], out["cust"], out["sales"]] if v is not None)
    return out

def csindex_meta(code):
    """中证指数基本信息：全称/类型(价格or全收益)/基日/基点"""
    import json as _j
    url = f"https://www.csindex.com.cn/csindex-home/index-list/index-basic-info/{code}"
    try:
        js = _j.loads(get(url, referer="https://www.csindex.com.cn/"))
        d = js.get("data") or {}
        return {k: d.get(k) for k in ["indexNameCn","indexFullNameCn","indexType","baseDate","basePoint","indexSeries","indexCurrency"]}
    except Exception as e:
        return {"err": str(e)[:60]}
