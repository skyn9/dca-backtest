# -*- coding: utf-8 -*-
"""具体数据源实现。每个类覆盖一个赛道。"""
from __future__ import annotations
import re, json
import pandas as pd
from .base import Source, register, http_get


@register
class FundSource(Source):
    """天天基金场外基金 —— 覆盖全部公募品类（宽基/行业/QDII/债券/商品/FOF）。

    净值为复权净值（由日涨幅累乘得到），已含分红再投资与全部费用。
    code: 6 位基金代码，如 '009051'
    """
    key = "fund"
    label = "天天基金·场外基金（复权净值，已含分红与费用）"
    total_return = True

    def _raw(self, code: str) -> str:
        return http_get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js",
                        referer=f"https://fund.eastmoney.com/{code}.html")

    def _fetch(self, code: str) -> pd.DataFrame:
        s = self._raw(code)
        m = re.search(r"var\s+Data_netWorthTrend\s*=\s*(\[.*?\]);", s, re.S)
        if not m:
            raise RuntimeError(f"fund {code}: 无净值数据（代码是否正确？货币基金不支持）")
        d = pd.DataFrame(json.loads(m.group(1)))
        d["date"] = (pd.to_datetime(d["x"], unit="ms", utc=True)
                     .dt.tz_convert("Asia/Shanghai").dt.tz_localize(None).dt.normalize())
        ret = pd.to_numeric(d["equityReturn"], errors="coerce").fillna(0.0)
        d["px"] = (1 + ret / 100.0).cumprod()      # 复权净值
        return d[["date", "px"]]

    def meta(self, code: str) -> dict:
        out = {}
        try:
            s = self._raw(code)
            for k, tag in [("fS_name", "name"), ("fund_Rate", "buy_fee")]:
                mm = re.search(rf'var\s+{k}\s*=\s*"?([^";]*)"?;', s)
                if mm:
                    out[tag] = mm.group(1)
            mm = re.search(r"var\s+Data_fluctuationScale\s*=\s*(\{.*?\});", s, re.S)
            if mm:
                fs = json.loads(mm.group(1))
                ser = fs.get("series") or []
                if ser:
                    out["scale_yi"] = ser[-1].get("y")
        except Exception:
            pass
        try:
            out.update(self.fees(code))
        except Exception:
            pass
        return out

    def fees(self, code: str) -> dict:
        """管理费/托管费/销售服务费（年%）与申购优惠费率。"""
        h = http_get(f"https://fundf10.eastmoney.com/jjfl_{code}.html",
                     referer="https://fundf10.eastmoney.com/")
        t = re.sub(r"&nbsp;", " ", re.sub(r"<[^>]+>", " ", h))
        t = re.sub(r"\s+", " ", t)
        def pc(lbl):
            m = re.search(lbl + r"\s*([\d.]+)%", t)
            return float(m.group(1)) if m else None
        o = {"mgmt": pc("管理费率"), "cust": pc("托管费率"), "sales": pc("销售服务费率")}
        o["annual_fee"] = sum(v for v in o.values() if v is not None) / 100.0
        m = re.search(r"申购费率.*?小于100万元\s*([\d.]+)%\s*\|\s*([\d.]+)%", t)
        if m:
            o["buy_std"], o["buy_disc"] = float(m.group(1)) / 100, float(m.group(2)) / 100
        return o


@register
class CSIndexSource(Source):
    """中证指数官网 —— A股/港股通指数，含全收益(H 开头)与价格指数。

    ⚠ 该站限流严格，务必依赖缓存，勿高频调用。
    code: 如 'H00922'(中证红利全收益) / '000300'(沪深300价格)
    """
    key = "csindex"
    label = "中证指数官网（H 开头为全收益）"

    def _fetch(self, code: str) -> pd.DataFrame:
        txt = http_get("https://www.csindex.com.cn/csindex-home/perf/index-perf"
                       f"?indexCode={code}&startDate=19900101&endDate=20991231",
                       referer="https://www.csindex.com.cn/")
        data = (json.loads(txt).get("data") or [])
        if not data:
            raise RuntimeError(f"csindex {code}: 空响应（限流或代码无效）")
        d = pd.DataFrame(data)
        col = "tclose" if "tclose" in d.columns else "close"
        d = d[["tradeDate", col]].rename(columns={"tradeDate": "date", col: "px"})
        d["date"] = pd.to_datetime(d["date"], format="%Y%m%d", errors="coerce")
        d["px"] = pd.to_numeric(d["px"], errors="coerce")
        d = d[d["date"] > "2000-01-01"]          # 剔除基期占位行
        return d[["date", "px"]]


@register
class SinaUSSource(Source):
    """新浪财经·美股指数。code: '.INX'(标普500) '.IXIC'(纳斯达克综合) '.DJI' '.NDX'"""
    key = "sina_us"
    label = "新浪·美股指数（价格指数，需另给股息率）"

    def _fetch(self, code: str) -> pd.DataFrame:
        import akshare as ak
        d = ak.index_us_stock_sina(symbol=code)[["date", "close"]]
        d.columns = ["date", "px"]
        d["date"] = pd.to_datetime(d["date"])
        return d


@register
class SinaHKSource(Source):
    """新浪财经·港股指数。code: 'HSI' 'HSCEI' 'HSTECH'"""
    key = "sina_hk"
    label = "新浪·港股指数（价格指数）"

    def _fetch(self, code: str) -> pd.DataFrame:
        import akshare as ak
        d = ak.stock_hk_index_daily_sina(symbol=code)[["date", "close"]]
        d.columns = ["date", "px"]
        d["date"] = pd.to_datetime(d["date"])
        return d


@register
class SinaFuturesSource(Source):
    """新浪财经·国内期货主力连续 —— 商品赛道。

    code: 'AU0'(沪金 2008起) 'AG0'(沪银) 'CU0'(沪铜 2005起) 'SC0'(原油) 'RB0'(螺纹)
    注意：主力连续含移仓损益，作为商品价格代理需在配置里用 tracking_diff 校准。
    """
    key = "sina_fut"
    label = "新浪·国内期货主力连续（商品）"

    def _fetch(self, code: str) -> pd.DataFrame:
        t = http_get("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/x/"
                     f"InnerFuturesNewService.getDailyKLine?symbol={code}",
                     referer="https://finance.sina.com.cn/")
        m = re.search(r"x\((\[.*\])\)", t, re.S)
        if not m:
            raise RuntimeError(f"sina_fut {code}: 解析失败")
        d = pd.DataFrame(json.loads(m.group(1)))[["d", "c"]]
        d.columns = ["date", "px"]
        d["date"] = pd.to_datetime(d["date"])
        d["px"] = pd.to_numeric(d["px"])
        return d


@register
class AkshareSource(Source):
    """通用逃生舱：直接调用任意 akshare 函数。

    code 形如 'index_zh_a_hist|symbol=000300,period=daily' —— 竖线前是函数名，
    后面是关键字参数。返回的表需含日期列与收盘列（自动识别）。
    """
    key = "akshare"
    label = "akshare 通用适配（任意接口）"

    def _fetch(self, code: str) -> pd.DataFrame:
        import akshare as ak
        fn, _, argstr = code.partition("|")
        kw = {}
        for pair in filter(None, argstr.split(",")):
            k, _, v = pair.partition("=")
            kw[k.strip()] = v.strip()
        d = getattr(ak, fn.strip())(**kw)
        dcol = next((c for c in d.columns if str(c) in ("date", "日期", "trade_date", "交易时间")), None)
        pcol = next((c for c in d.columns if str(c) in ("close", "收盘", "收盘价", "px", "最新价", "晚盘价")), None)
        if dcol is None or pcol is None:
            raise RuntimeError(f"akshare {fn}: 无法识别日期/收盘列，实际列为 {list(d.columns)}")
        out = d[[dcol, pcol]].copy()
        out.columns = ["date", "px"]
        out["date"] = pd.to_datetime(out["date"])
        out["px"] = pd.to_numeric(out["px"], errors="coerce")
        return out
