"""把一次完整分析渲染成自包含的 HTML 报告。"""
from __future__ import annotations

import datetime
import html
import json

import pandas as pd

from .. import analysis as A
from ..engine import dca_path, rolling_dca
from .template import CSS, JS


def PCT(v, d=2):
    """百分比格式化；None/NaN 显示为破折号。"""
    return "—" if v is None or v != v else f"{v*100:.{d}f}%"


def _cls(v, good=0.0):
    if v is None or v != v:
        return ""
    return "pos" if v > good else ("neg" if v < 0 else "")


def build(portfolio, *, use_proxy: bool = False, horizons=(3, 5, 10, 15),
          horizon: int = 10, forward: int = 20, n_boot: int = 2000,
          n_mc: int = 3000, n_pert: int = 80, benchmark: pd.Series | None = None,
          start: str | None = None, end: str | None = None) -> str:
    p = portfolio
    r = p.returns(start=start, end=end, use_proxy=use_proxy)
    w = p.weights
    blend = p.blend(r)
    yrs = len(r) / 12.0
    D: dict = {}

    # ---- 定投轨迹 ----
    H, irr = dca_path(r, w, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    D["dca"] = {"dates": [d.strftime("%Y-%m") for d in H.index],
                "cost": [round(float(x)) for x in H["cost"]],
                "port": [round(float(x)) for x in H["value"]],
                "hs": None, "xs": 2 if yrs > 12 else 1}
    bench_irr = None
    if benchmark is not None:
        b = benchmark.reindex(r.index).dropna()
        if len(b) > 24:
            Hb, bench_irr = dca_path(b, monthly=p.monthly_amount, buy_fee=p.buy_fee)
            D["dca"]["hs"] = [round(float(x)) for x in Hb["value"].reindex(H.index).ffill()]

    # ---- 滚动 ----
    tab = A.rolling_table(r, w, horizons=horizons, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    rd = rolling_dca(blend, None, horizon * 12, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    D["roll"] = {"dates": [d.strftime("%Y-%m") for d in rd["start"]],
                 "port": [round(float(x), 4) for x in rd["irr"]]} if len(rd) else None

    # ---- 起点敏感性 ----
    px = p.monthly(use_proxy=use_proxy).dropna()
    y0, y1 = px.index.min().year, px.index.max().year
    cand = [y for y in (y0, y0 + 3, y0 + 6, y0 + 8) if y <= y1 - horizon - 1]
    sens = None
    if len(cand) >= 2:
        starts = {f"{y}起": f"{y}-01-01" for y in cand}
        sens = A.asset_start_sensitivity(p, starts, horizon_y=horizon, use_proxy=use_proxy,
                                         monthly=p.monthly_amount, buy_fee=p.buy_fee)
        vc = [c for c in sens.columns if c not in ("name", "kind", "lo", "hi", "range")]
        D["sens"] = {"starts": vc, "rows": [
            {"name": x["name"], "kind": x["kind"], "v": [None if x[c] != x[c] else round(float(x[c]), 4) for c in vc],
             "lo": round(float(x["lo"]), 4), "hi": round(float(x["hi"]), 4),
             "range": round(float(x["range"]), 4)} for _, x in sens.iterrows()]}

    # ---- 全周期矩阵 ----
    mx = A.year_horizon_matrix(r, w, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    if not mx.empty:
        D["matrix"] = {"years": [int(y) for y in mx.index], "hor": [int(c) for c in mx.columns],
                       "vals": [[None if v != v else round(float(v), 4) for v in row] for _, row in mx.iterrows()]}

    D["corr"] = {"labels": list(r.columns),
                 "m": [[round(float(r.corr().iloc[i, j]), 2) for j in range(r.shape[1])] for i in range(r.shape[1])]}

    # ---- 稳健性 ----
    pert = A.weight_perturbation(r, w, horizon_y=horizon, n=n_pert,
                                 monthly=p.monthly_amount, buy_fee=p.buy_fee)
    try:
        boot = A.block_bootstrap(blend, horizon_y=horizon, n_paths=n_boot,
                                 monthly=p.monthly_amount, buy_fee=p.buy_fee)
    except Exception:
        boot = None
    eq = [c for c in r.columns if "债" not in c]
    mc = {}
    for tag, f in [("历史重演", 1.0), ("股票打8折", 0.8), ("股票打6折", 0.6)]:
        s = A.monte_carlo(r, w, years=forward, n_paths=n_mc,
                          shock=dict.fromkeys(eq, f) if f != 1.0 else None,
                          monthly=p.monthly_amount, buy_fee=p.buy_fee)
        mc[tag] = s

    # ================= HTML =================
    esc = html.escape
    row10 = tab[tab["years"] == horizon]
    med10 = float(row10["med"].iloc[0]) if len(row10) else float("nan")
    min10 = float(row10["min"].iloc[0]) if len(row10) else float("nan")
    rng = D.get("sens", {}).get("rows")
    prng = next((x["range"] for x in rng if x["kind"] == "portfolio"), None) if rng else None
    zero_from = None
    if not mx.empty:
        for h in mx.columns:
            v = mx[h].dropna()
            if len(v) and (v > 0).all():
                zero_from = int(h)
                break

    P_ = PCT
    parts = [f"<title>{esc(p.name)} · 定投回测报告</title>",
             '<link rel="preconnect" href="https://fonts.googleapis.com">',
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Spectral:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">',
             f"<style>{CSS}</style>", '<div class="wrap">']

    parts.append(f"""
<header>
  <div class="kicker"><span class="eyebrow">定投回测报告</span><i></i>
    <span class="eyebrow">{datetime.date.today()}</span></div>
  <h1>{esc(p.name)}</h1>
  <p class="lede">{len(p.assets)} 类资产 · 月投 {p.monthly_amount:,.0f} 元 ·
    回测窗口 {r.index.min().date()} 至 {r.index.max().date()}（{yrs:.1f} 年）·
    口径 {"长历史代理" if use_proxy else "实际产品净值"}。
    下面的重点不是「历史赚了多少」，而是<b>换个起点、改个权重、换段数据，结论还成不成立</b>。</p>
  <div class="kpis">
    <div class="kpi hi"><b>{P_(med10)}</b><span>{horizon} 年定投 IRR 中位数</span></div>
    <div class="kpi"><b>{P_(min10)}</b><span>{horizon} 年定投最差情况</span></div>
    <div class="kpi hi"><b>{(f'{prng*100:.2f}pp' if prng is not None else '—')}</b><span>不同起点下中位收益的极差<br>（越小 = 越不靠运气）</span></div>
    <div class="kpi"><b>{(f'{zero_from} 年' if zero_from else '—')}</b><span>持有多久后所有起投年均为正</span></div>
    <div class="kpi"><b>{P_(p.weighted_fee(use_proxy))}</b><span>加权年持有成本</span></div>
  </div>
  <div class="note warn"><b>历史回测不是预期。</b>本页所有历史数字都受回测窗口影响；
    面向未来的合理预期请看第 5 节的蒙特卡洛「打折」情景，它通常比历史中位数低 3–5 个百分点。</div>
</header>""")

    # 01 组合
    rows = "".join(
        f"<tr><td><b>{esc(a.name)}</b></td><td class='n em'>{a.weight*100:.0f}%</td>"
        f"<td style='width:60px'><i class='wbar' style='width:{a.weight/max(x.weight for x in p.assets)*100:.0f}%'></i></td>"
        f"<td class='n'>{esc(a.source)}</td><td class='n'>{esc(str(a.code))}</td>"
        f"<td class='n'>{PCT(a.gross_drag)}</td><td class='wide'>{esc(a.note)}</td></tr>"
        for a in p.resolved(use_proxy))
    parts.append(f"""
<section><hr><div class="h-wrap"><span class="h-num">01</span><h2>组合构成</h2></div>
<div class="tw"><table><caption>「年拖累」= 模拟基金年费 + 跟踪差。用基金净值回测时为 0（费用已含在净值里）。</caption>
<thead><tr><th>资产</th><th>权重</th><th></th><th>数据源</th><th>代码</th><th>年拖累</th><th>备注</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<figure><div class="lg"><span><i style="background:var(--gold)"></i>本组合</span>
{'<span><i style="background:var(--blue)"></i>基准</span>' if D["dca"]["hs"] else ''}
<span><i style="background:var(--muted)"></i>累计本金</span></div>
<svg id="cDca" class="chart" viewBox="0 0 1000 350" role="img"
 aria-label="定投账户市值走势：投入{H['cost'].iloc[-1]:,.0f}元，终值{H['value'].iloc[-1]:,.0f}元"></svg>
<figcaption>每月定投 {p.monthly_amount:,.0f} 元，累计投入 <span class="mono">{H['cost'].iloc[-1]:,.0f}</span> 元，
期末 <span class="mono">{H['value'].iloc[-1]:,.0f}</span> 元，IRR <span class="mono">{P_(irr)}</span>
{f'；基准 IRR <span class="mono">{P_(bench_irr)}</span>' if bench_irr else ''}。</figcaption></figure></section>""")

    # 02 滚动
    tr = "".join(
        f"<tr><td><b>{int(x['years'])} 年</b></td><td class='n em'>{P_(x['med'])}</td>"
        f"<td class='n'>{P_(x['p10'])}</td><td class='n'>{P_(x['p90'])}</td>"
        f"<td class='n {_cls(x['min'])}'>{P_(x['min'])}</td>"
        f"<td class='n {'pos' if x['loss_prob']==0 else 'neg'}'>{P_(x['loss_prob'],1)}</td>"
        f"<td class='n'>{P_(x['med_maxdd'],1)}</td><td class='n'>{int(x['n'])}</td></tr>"
        for _, x in tab.iterrows())
    parts.append(f"""
<section><hr><div class="h-wrap"><span class="h-num">02</span><h2>滚动定投：每一个起点都算一遍</h2></div>
<p class="dek">把窗口内每个月都当作起投点，各持有固定期限。「中位浮亏」= 定投过程中账户相对累计投入的最大浮亏中位数。</p>
<div class="tw"><table><thead><tr><th>期限</th><th>中位 IRR</th><th>10% 分位</th><th>90% 分位</th>
<th>最差</th><th>亏损概率</th><th>中位浮亏</th><th>起点数</th></tr></thead><tbody>{tr}</tbody></table></div>
{'<figure><svg id="cRoll" class="chart" viewBox="0 0 1000 300" role="img" aria-label="按起投月份排列的定投年化收益"></svg><figcaption>横轴是「哪个月开始定投」，纵轴是满 ' + str(horizon) + ' 年后的年化 IRR。曲线越平，说明结果越不取决于入场时点。</figcaption></figure>' if D["roll"] else ''}
</section>""")

    # 03 起点敏感性
    if sens is not None:
        vc = D["sens"]["starts"]
        sr = "".join(
            f"<tr class='{'hl' if x['kind']=='portfolio' else ''}'><td>{esc(x['name'])}</td>"
            + "".join(f"<td class='n'>{P_(v)}</td>" for v in x["v"])
            + f"<td class='n'>{P_(x['lo'])}–{P_(x['hi'])}</td>"
              f"<td class='n {'em' if x['kind']=='portfolio' else ''}'>{x['range']*100:.2f}pp</td></tr>"
            for x in sorted(D["sens"]["rows"], key=lambda z: z["range"]))
        parts.append(f"""
<section><hr><div class="h-wrap"><span class="h-num">03</span><h2>起点敏感性</h2></div>
<p class="dek">同一资产、同样的持有方式，只因开始的年份不同，结果可以差出好几倍。
统一口径：该窗口内滚动 {horizon} 年定投 IRR 的中位数。<b>极差越小 = 结果越不取决于运气。</b></p>
<figure><svg id="cSens" class="chart" viewBox="0 0 1000 400" role="img"
 aria-label="各资产在不同起点窗口下的收益区间对比"></svg>
<figcaption>线段两端是该资产在各起点窗口中的最低与最高值，圆点是实际取值。线段越短越好。</figcaption></figure>
<div class="tw"><table><thead><tr><th>资产 / 组合</th>
{''.join(f'<th>{esc(c)}</th>' for c in vc)}<th>区间</th><th>极差</th></tr></thead><tbody>{sr}</tbody></table></div></section>""")

    # 04 矩阵
    if "matrix" in D:
        agg = "".join(
            f"<tr><td><b>{int(h)} 年</b></td><td class='n'>{P_(mx[h].dropna().max())}</td>"
            f"<td class='n em'>{P_(mx[h].dropna().median())}</td>"
            f"<td class='n {_cls(mx[h].dropna().min())}'>{P_(mx[h].dropna().min())}</td>"
            f"<td class='n'>{int((mx[h].dropna()<0).sum())} / {len(mx[h].dropna())}</td></tr>"
            for h in mx.columns if len(mx[h].dropna()))
        parts.append(f"""
<section><hr><div class="h-wrap"><span class="h-num">04</span><h2>全周期矩阵</h2></div>
<p class="dek">每格 =「从该年 1 月开始定投、持有该期限」的年化 IRR。你可以直接找到打算开始的那一年，横着读过去。</p>
<div class="tw"><div id="mx"></div></div>
<div class="tw"><table style="margin-top:26px"><caption>此表按整年 1 月起投，样本少于第 02 节的逐月滚动，两者结论一致时才可采信。</caption>
<thead><tr><th>持有期限</th><th>最好</th><th>中位</th><th>最差</th><th>亏损年数</th></tr></thead>
<tbody>{agg}</tbody></table></div></section>""")

    # 05 稳健性
    def _pert_row(x):
        is_base = x["level"] == "基准"
        rng_txt = "—" if is_base else f"{P_(x['med_lo'])} ~ {P_(x['med_hi'])}"
        delta = "—" if is_base else f"{x['vs_base'] * 100:+.2f}pp"
        flag = "是" if x["all_positive"] else "否"
        return (f"<tr><td>{esc(str(x['level']))}</td><td class='n'>{rng_txt}</td>"
                f"<td class='n em'>{P_(x['med_mean'])}</td><td class='n'>{delta}</td>"
                f"<td class='n'>{P_(x['min_mean'])}</td>"
                f"<td class='{'pos' if x['all_positive'] else 'neg'}'>{flag}</td></tr>")

    pr = "".join(_pert_row(x) for _, x in pert.iterrows())
    mcr = "".join(
        f"<tr><td>{esc(t)}</td><td class='n em'>{P_(s.median())}</td><td class='n'>{P_(s.quantile(.05))}</td>"
        f"<td class='n'>{P_(s.quantile(.25))}</td><td class='n'>{P_(s.quantile(.75))}</td>"
        f"<td class='n {'pos' if (s<0).mean()<0.02 else ''}'>{P_((s<0).mean(),2)}</td></tr>"
        for t, s in mc.items())
    bootline = (f"{n_boot} 条重采样路径：中位 <span class='mono'>{P_(boot.median())}</span>，"
                f"5% 分位 <span class='mono'>{P_(boot.quantile(.05))}</span>，"
                f"亏损概率 <span class='mono'>{P_((boot<0).mean(),2)}</span>。"
                f"该数通常高于滚动窗口的结果——洗牌破坏了真实历史中的均值回归，是更保守的估计。"
                if boot is not None else "序列过短，跳过。")
    parts.append(f"""
<section><hr><div class="h-wrap"><span class="h-num">05</span><h2>稳健性检验</h2></div>
<p class="dek">下面三项专门用来拆穿「事后诸葛亮」。</p>
<h3 style="font-family:var(--sf);font-size:17px;margin-top:26px">权重扰动 · 结论依赖精确权重吗</h3>
<div class="tw"><table><caption>每档随机生成 {n_pert} 组权重（基准上加均匀噪声后归一化），各自跑完整滚动定投。</caption>
<thead><tr><th>扰动</th><th>中位 IRR 范围</th><th>中位均值</th><th>对比基准</th><th>最差均值</th><th>全部为正</th></tr></thead>
<tbody>{pr}</tbody></table></div>
<h3 style="font-family:var(--sf);font-size:17px;margin-top:30px">Block Bootstrap · 平行历史</h3>
<p class="dek" style="margin-top:8px">{bootline}</p>
<h3 style="font-family:var(--sf);font-size:17px;margin-top:30px">蒙特卡洛前瞻 {forward} 年 · <b>这才是预期</b></h3>
<div class="tw"><table><caption>保留资产间协方差结构，按历史均值（可打折）模拟 {n_mc} 条路径。</caption>
<thead><tr><th>情景</th><th>中位</th><th>5% 分位</th><th>25% 分位</th><th>75% 分位</th><th>亏损概率</th></tr></thead>
<tbody>{mcr}</tbody></table></div>
<div class="note"><b>请用「打8折」那一行做规划，而不是历史中位数。</b>
历史窗口往往包含了某类资产的超常周期（如 2008 年以来的美股科技），未来重复的概率不高。</div></section>""")

    # 06 相关性
    parts.append("""
<section><hr><div class="h-wrap"><span class="h-num">06</span><h2>相关性</h2></div>
<p class="dek">月度收益相关系数。金色越深＝越同涨同跌，蓝色＝反向。<b>找零和负数，比找高收益更重要。</b></p>
<div class="tw"><div id="corr" class="heat"></div></div></section>""")

    parts.append(f"""
<footer><p><b>免责声明。</b>本页由 <span class="mono">dca</span> 回测框架自动生成，是历史数据的分析结果，
<b>不构成投资建议</b>。回测有其固有局限：滚动窗口样本高度重叠、存在生存者偏差、
历史收益率（尤其是债券）大概率不可持续。实际结果取决于你何时开始、能否坚持，
以及未来真实发生了什么。请根据自身情况判断，必要时咨询有资质的投资顾问。</p>
<p style="margin-top:14px" class="mono">窗口 {r.index.min().date()} → {r.index.max().date()}（{len(r)} 个月）·
{len(p.assets)} 类资产 · 生成于 {datetime.datetime.now():%Y-%m-%d %H:%M}</p></footer>
</div><div class="tip" id="tip"></div>
<script>{JS.replace('__DATA__', json.dumps(D, ensure_ascii=False, separators=(',', ':')))}</script>""")
    return "\n".join(parts)
