# -*- coding: utf-8 -*-
"""命令行入口：dca <command> -c <config.yaml>"""
from __future__ import annotations
import argparse, sys, os
import numpy as np
import pandas as pd

from .portfolio import Portfolio
from . import analysis as A
from .engine import rolling_dca, dca_path, perf_stats
from .sources import available

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

PCT = lambda v, d=2: "—" if v != v else f"{v*100:.{d}f}%"
BAR = "─" * 96


def _p(cfg, cache):
    return Portfolio.from_yaml(cfg, cache_dir=cache)


def _returns(p, args, need_years: float = 0):
    """取收益率矩阵，并在样本不足时给出明确提示。"""
    use_proxy = getattr(args, "proxy", False)
    if use_proxy and not p.has_proxy():
        print("※ 该配置未定义 proxy，--proxy 无效，仍用主数据源\n")
        use_proxy = False
    r = p.returns(start=getattr(args, "start", None), end=getattr(args, "end", None),
                  use_proxy=use_proxy)
    yrs = len(r) / 12.0
    tag = "代理(长历史)" if use_proxy else "实际产品"
    print(f"窗口 {r.index.min().date()} ~ {r.index.max().date()}"
          f"（{len(r)} 个月 / {yrs:.1f} 年，口径：{tag}）")
    if need_years and yrs < need_years:
        print(f"\n⚠ 样本仅 {yrs:.1f} 年，做 {need_years:.0f} 年期检验会严重不足。")
        if p.has_proxy() and not use_proxy:
            print("  该配置已定义长历史代理，请加 --proxy 重跑：")
            print(f"  python -m dca {args.cmd} -c {args.config} --proxy")
        else:
            print("  建议改用 configs/research_longhistory.yaml（指数代理，18.7 年），")
            print("  或给各资产补上 proxy 字段。短样本下的结论不可信。")
        print()
    return r


def cmd_sources(args):
    print("可用数据源：\n")
    for k, v in available().items():
        print(f"  {k:12s} {v}")
    print("\n在 yaml 里用 `source: <key>` 指定。新增赛道只需实现一个 Source 子类。")


def cmd_fetch(args):
    p = _p(args.config, args.cache)
    print(f"[{p.name}] 抓取 {len(p.assets)} 个资产 → {args.cache}/")
    print("提示：默认每次请求间隔 3 秒，请勿调低（环境变量 DCA_MIN_GAP）\n")
    p.fetch(force=args.force, verbose=True, use_proxy=args.proxy)
    if args.proxy is False and p.has_proxy():
        print("\n  该配置还定义了长历史代理，一并抓取：")
        p.fetch(force=args.force, verbose=True, use_proxy=True)
    px = p.monthly(use_proxy=args.proxy).dropna()
    print(f"\n公共窗口 {px.index.min().date()} ~ {px.index.max().date()}  "
          f"{len(px)} 个月（{len(px)/12:.1f} 年）")


def cmd_run(args):
    p = _p(args.config, args.cache)
    print(f"\n[{p.name}] 月投 {p.monthly_amount:,.0f} 元 · 申购费 {p.buy_fee*100:.2f}% "
          f"· 加权年拖累 {p.weighted_fee(getattr(args,'proxy',False))*100:.2f}%")
    r = _returns(p, args, need_years=max(args.horizons) + 3)
    w = p.weights

    print(f"\n{BAR}\n【各资产表现】")
    st = perf_stats(r).sort_values("cagr", ascending=False)
    print(f"{'资产':<16}{'年化':>9}{'波动':>9}{'最大回撤':>10}{'Sharpe':>9}{'月数':>7}")
    for _, x in st.iterrows():
        print(f"{x['asset']:<16}{PCT(x['cagr']):>9}{PCT(x['vol']):>9}{PCT(x['mdd']):>10}"
              f"{x['sharpe']:>9.2f}{x['months']:>7}")

    print(f"\n{BAR}\n【组合滚动定投】")
    tab = A.rolling_table(r, w, horizons=args.horizons)
    print(f"{'期限':<8}{'中位IRR':>10}{'10%分位':>10}{'90%分位':>10}{'最差':>10}"
          f"{'亏损率':>9}{'中位浮亏':>10}{'起点数':>8}")
    for _, x in tab.iterrows():
        print(f"{x['label']:<8}{PCT(x['med']):>10}{PCT(x['p10']):>10}{PCT(x['p90']):>10}"
              f"{PCT(x['min']):>10}{PCT(x['loss_prob'],1):>9}{PCT(x['med_maxdd'],1):>10}{x['n']:>8}")

    H, irr = dca_path(r, w, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    print(f"\n全程定投：投入 {H['cost'].iloc[-1]:,.0f} → 终值 {H['value'].iloc[-1]:,.0f}  "
          f"IRR {PCT(irr)}")

    print(f"\n{BAR}\n【相关性】(月度收益)")
    print((r.corr() * 100).round(0).astype(int).to_string())


def cmd_test(args):
    """全套稳健性检验——这是本框架的主命令。"""
    p = _p(args.config, args.cache)
    print(f"\n[{p.name}] 稳健性检验")
    r = _returns(p, args, need_years=args.horizon + 5)
    w = p.weights

    # 1 起点敏感性
    print(f"\n{BAR}\n【1/5 起点敏感性】同一组合，换起点结果差多少（极差越小越好）")
    px = p.monthly(use_proxy=getattr(args, "proxy", False)).dropna()
    y0 = px.index.min().year
    starts = {f"{y}起": f"{y}-01-01" for y in
              [y0, y0 + 3, y0 + 6, y0 + 8] if y <= px.index.max().year - args.horizon - 1}
    if len(starts) >= 2:
        sens = A.asset_start_sensitivity(p, starts, horizon_y=args.horizon,
                                         use_proxy=getattr(args, "proxy", False),
                                         monthly=p.monthly_amount, buy_fee=p.buy_fee)
        cols = [c for c in sens.columns if c not in ("name", "kind", "lo", "hi", "range")]
        print(f"{'资产/组合':<18}" + "".join(f"{c:>10}" for c in cols) + f"{'区间':>18}{'极差':>10}")
        for _, x in sens.iterrows():
            mark = "★ " if x["kind"] == "portfolio" else "  "
            print(f"{mark}{x['name']:<16}" + "".join(f"{PCT(x[c]):>10}" for c in cols) +
                  f"{PCT(x['lo'])+'–'+PCT(x['hi']):>18}{x['range']*100:>9.2f}pp")
    else:
        print("  数据窗口太短，跳过")

    # 2 全周期矩阵
    print(f"\n{BAR}\n【2/5 全周期矩阵】起投年 × 持有期限 的定投 IRR")
    mx = A.year_horizon_matrix(r, w, monthly=p.monthly_amount, buy_fee=p.buy_fee)
    if not mx.empty:
        print("起投年  " + "".join(f"{h:>7}年" for h in mx.columns))
        for y, row in mx.iterrows():
            print(f"{y}   " + "".join(("     — " if v != v else f"{v*100:6.1f}%") for v in row))
        print("\n按期限汇总：")
        print(f"{'期限':<8}{'最好':>9}{'中位':>9}{'最差':>9}{'亏损年数':>10}")
        for h in mx.columns:
            v = mx[h].dropna()
            if len(v) == 0: continue
            print(f"{h:<3}年   {PCT(v.max()):>9}{PCT(v.median()):>9}{PCT(v.min()):>9}"
                  f"{int((v<0).sum()):>6}/{len(v):<4}")

    # 3 权重扰动
    print(f"\n{BAR}\n【3/5 权重扰动】随机推移权重，看结论是否依赖精确权重")
    pert = A.weight_perturbation(r, w, horizon_y=args.horizon, n=args.n_pert,
                                 monthly=p.monthly_amount, buy_fee=p.buy_fee)
    print(f"{'扰动':<10}{'中位IRR范围':>22}{'中位均值':>11}{'对比基准':>11}{'最差均值':>11}{'全部为正':>10}")
    for _, x in pert.iterrows():
        rng = "—" if x["level"] == "基准" else f"{PCT(x['med_lo'])} ~ {PCT(x['med_hi'])}"
        delta = "—" if x["level"] == "基准" else f"{x['vs_base']*100:+.2f}pp"
        flag = "是" if x["all_positive"] else "否"
        print(f"{x['level']:<10}{rng:>22}{PCT(x['med_mean']):>11}{delta:>11}"
              f"{PCT(x['min_mean']):>11}{flag:>10}")

    # 4 Bootstrap
    print(f"\n{BAR}\n【4/5 Block Bootstrap】按 12 月为块重采样，生成平行历史")
    try:
        b = A.block_bootstrap(p.blend(r), horizon_y=args.horizon, n_paths=args.n_boot,
                              monthly=p.monthly_amount, buy_fee=p.buy_fee)
        print(f"  {args.n_boot} 条路径：中位 {PCT(b.median())}  5%分位 {PCT(b.quantile(.05))}  "
              f"95%分位 {PCT(b.quantile(.95))}  亏损概率 {PCT((b<0).mean(),2)}")
    except Exception as e:
        print(f"  跳过：{e}")

    # 5 蒙特卡洛前瞻
    print(f"\n{BAR}\n【5/5 蒙特卡洛前瞻 {args.forward} 年】历史收益打折后的未来分布")
    print(f"{'情景':<18}{'中位':>10}{'5%分位':>10}{'25%分位':>10}{'75%分位':>10}{'亏损概率':>11}")
    eq = [c for c in r.columns if "债" not in c and "bond" not in c.lower()]
    for tag, f in [("历史重演", 1.0), ("股票打8折", 0.8), ("股票打6折", 0.6)]:
        shock = {c: f for c in eq} if f != 1.0 else None
        mc = A.monte_carlo(r, w, years=args.forward, n_paths=args.n_mc, shock=shock,
                           monthly=p.monthly_amount, buy_fee=p.buy_fee)
        print(f"{tag:<18}{PCT(mc.median()):>10}{PCT(mc.quantile(.05)):>10}"
              f"{PCT(mc.quantile(.25)):>10}{PCT(mc.quantile(.75)):>10}{PCT((mc<0).mean(),2):>11}")
    print(f"\n※ 历史回测反映过去；蒙特卡洛的「打折」情景更接近合理预期。请勿用历史中位数做规划。")


def cmd_optimize(args):
    p = _p(args.config, args.cache)
    print(f"\n[{p.name}] 权重优化")
    r = _returns(p, args, need_years=args.horizon + 5)
    print(f"目标 = 最大化滚动{args.horizon}年定投IRR的{args.objective}")
    print(f"约束：单资产 ≤ {args.max_weight*100:.0f}%\n")
    w, tab = A.optimize_weights(r, horizon_y=args.horizon, objective=args.objective,
                                n_iter=args.n_iter, max_weight=args.max_weight,
                                monthly=p.monthly_amount, buy_fee=p.buy_fee)
    print(f"{'资产':<16}{'优化权重':>10}{'当前权重':>10}{'偏离':>10}")
    for c, v in zip(r.columns, w):
        cur = p.weights[c]
        print(f"{c:<16}{v*100:>9.1f}%{cur*100:>9.1f}%{(cur-v)*100:>+9.1f}pp")
    print(f"\n※ 优化权重是「回头看」的结果。请用 `dca walkforward` 检验它在样本外是否站得住——")
    print(f"  本项目的实测是：固定权重在样本外反而胜过训练段最优权重。")


def cmd_walkforward(args):
    p = _p(args.config, args.cache)
    print(f"\n[{p.name}] 样本外 Walk-Forward")
    r = _returns(p, args, need_years=14)
    yrs = sorted({d.year for d in r.index})
    if len(yrs) < 12:
        print("窗口不足 12 年，样本外检验意义有限"); return
    mid = yrs[len(yrs) // 2]
    splits = [(f"{yrs[0]}-01-01", f"{y}-12-31", f"{y+1}-01-01", f"{yrs[-1]}-12-31")
              for y in (mid - 1, mid, mid + 1) if y + 4 < yrs[-1]]
    print(f"{len(splits)} 组切分\n")
    wf = A.walk_forward(r, splits, fixed_weights=p.weights, n_iter=args.n_iter,
                        monthly=p.monthly_amount, buy_fee=p.buy_fee)
    if wf.empty:
        print("无有效切分"); return
    print(f"{'训练 → 测试':<30}{'训练段最优(样本外)':>20}{'★本方案(固定)':>16}{'等权':>10}{'最优-本方案':>13}")
    for _, x in wf.iterrows():
        print(f"{x['train']} → {x['test']:<12}{PCT(x['opt_out']):>20}{PCT(x['fixed_out']):>16}"
              f"{PCT(x['equal_out']):>10}{x['opt_minus_fixed']*100:>+12.2f}pp")
    print(f"{'平均':<30}{PCT(wf['opt_out'].mean()):>20}{PCT(wf['fixed_out'].mean()):>16}"
          f"{PCT(wf['equal_out'].mean()):>10}{wf['opt_minus_fixed'].mean()*100:>+12.2f}pp")
    d = wf["opt_minus_fixed"].mean()
    print(f"\n※ {'训练段最优权重在样本外并未胜出，说明优化出的差异多半是噪音。' if d <= 0.002 else '训练段最优权重在样本外仍有优势，可考虑采纳。'}")


def cmd_report(args):
    from .report import build
    p = _p(args.config, args.cache)
    print(f"\n[{p.name}] 生成报告…")
    bench = None
    if args.benchmark:
        from .sources import get_source
        src, _, code = args.benchmark.partition(":")
        d = get_source(src, args.cache).get(code)
        s_ = d.set_index("date")["px"].resample("ME").last().pct_change().dropna()
        bench = s_
    html_text = build(p, use_proxy=args.proxy, horizon=args.horizon, forward=args.forward,
                      n_boot=args.n_boot, n_mc=args.n_mc, n_pert=args.n_pert,
                      benchmark=bench, start=args.start, end=args.end)
    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                + html_text.split("</title>")[0] + "</title></head><body>"
                + "</title>".join(html_text.split("</title>")[1:]) + "</body></html>")
    print(f"已写出 {args.out}（{os.path.getsize(args.out)/1024:.0f} KB）")
    print("用浏览器打开即可；文件自包含，可直接分享。")


def build_parser():
    ap = argparse.ArgumentParser(prog="dca", description="定投组合回测与稳健性检验")
    ap.add_argument("--cache", default="data", help="数据缓存目录（默认 data/）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, horizon=10):
        sp.add_argument("-c", "--config", default="configs/default.yaml")
        sp.add_argument("--proxy", action="store_true",
                        help="改用配置里的长历史代理做回测（实盘仍买 code 指定的产品）")
        sp.add_argument("--start", default=None, help="回测起始，如 2010-01-01")
        sp.add_argument("--end", default=None)
        sp.add_argument("--horizon", type=int, default=horizon, help="主分析期限（年）")

    s = sub.add_parser("sources", help="列出可用数据源"); s.set_defaults(func=cmd_sources)
    s = sub.add_parser("fetch", help="抓取并缓存数据")
    s.add_argument("-c", "--config", default="configs/default.yaml")
    s.add_argument("--force", action="store_true", help="忽略缓存重新抓取")
    s.add_argument("--proxy", action="store_true", help="只抓长历史代理")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("run", help="基础回测"); common(s)
    s.add_argument("--horizons", type=int, nargs="+", default=[3, 5, 10, 15])
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("test", help="全套稳健性检验（主命令）"); common(s)
    s.add_argument("--forward", type=int, default=20, help="蒙特卡洛前瞻年数")
    s.add_argument("--n-pert", type=int, default=100)
    s.add_argument("--n-boot", type=int, default=3000)
    s.add_argument("--n-mc", type=int, default=4000)
    s.set_defaults(func=cmd_test)

    s = sub.add_parser("optimize", help="权重优化"); common(s)
    s.add_argument("--objective", default="p10", choices=["p10", "median", "min"])
    s.add_argument("--max-weight", type=float, default=0.35)
    s.add_argument("--n-iter", type=int, default=2500)
    s.set_defaults(func=cmd_optimize)

    s = sub.add_parser("walkforward", help="样本外检验"); common(s)
    s.add_argument("--n-iter", type=int, default=2000)
    s.set_defaults(func=cmd_walkforward)

    s = sub.add_parser("report", help="生成自包含 HTML 报告"); common(s)
    s.add_argument("-o", "--out", default="out/report.html")
    s.add_argument("--benchmark", default=None,
                   help="基准，形如 csindex:H00300 或 fund:000051")
    s.add_argument("--forward", type=int, default=20)
    s.add_argument("--n-pert", type=int, default=80)
    s.add_argument("--n-boot", type=int, default=2000)
    s.add_argument("--n-mc", type=int, default=3000)
    s.set_defaults(func=cmd_report)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except FileNotFoundError as e:
        print(f"找不到文件：{e}", file=sys.stderr); return 2
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
