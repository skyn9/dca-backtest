# dca — 定投组合回测与稳健性检验

一个用来回答**「这个定投组合到底靠不靠谱」**的框架。

它的重点不是算出某个组合历史年化多少——那个数字几乎总是被起点美化过——
而是回答：**换个时间开始还成立吗？权重错几个点会怎样？在模型没见过的数据上还站得住吗？**

## 为什么需要它

同一只沪深300基金，2005 年起投年化 9.5%，2008 年起投只有 2.0%。**差距不来自选基能力，来自运气。**
绝大多数「年化 XX%」的回测都没有回答这个问题。

本框架把四类反过拟合检验做成了一条命令：

| 检验 | 回答什么问题 |
|---|---|
| 起点敏感性 | 换个年份开始，结果差多少 |
| 全周期矩阵 | 任何一年入场、持有任何时长，分别是什么结果 |
| 权重扰动 | 权重错 3/5/8 个百分点，结论还成立吗 |
| 样本外 Walk-Forward | 训练段优化的权重，到新数据上是否失效 |
| Block Bootstrap | 在历史上没发生但可能发生的路径里表现如何 |
| 蒙特卡洛前瞻 | 未来 20 年的分布，含收益打折情景 |

## 快速开始

```bash
pip install -r requirements.txt

python -m dca sources                                   # 看有哪些数据源
python -m dca fetch -c configs/default.yaml             # 抓数据（仓库不含数据）
python -m dca run   -c configs/default.yaml --proxy     # 基础回测
python -m dca test  -c configs/default.yaml --proxy     # 全套稳健性检验 ← 主命令
python -m dca walkforward -c configs/default.yaml --proxy
python -m dca optimize    -c configs/default.yaml --proxy

# 生成自包含 HTML 报告（可直接分享，含全部图表）
python -m dca report -c configs/default.yaml --proxy \
       --benchmark csindex:H00300 -o out/report.html
```

`docs/example-report.html` 是一份完整的示例产出。

或者用 Python API 自己组装：

```python
from dca import Portfolio, analysis as A

p = Portfolio.from_yaml("configs/default.yaml")
r = p.returns(use_proxy=True)

print(A.rolling_table(r, p.weights))                    # 多期限滚动定投
print(A.asset_start_sensitivity(p, {"2008起": "2008-01-01",
                                    "2013起": "2013-01-01"}, use_proxy=True))
print(A.weight_perturbation(r, p.weights))              # 权重扰动
print(A.monte_carlo(r, p.weights, years=20, shock={"美股纳指100": 0.6}))
```

## 定义一个组合

```yaml
name: 我的组合
monthly_amount: 2000
assets:
  - {name: A股红利, source: fund,     code: "009051", weight: 0.28}
  - {name: 标普500, source: fund,     code: "017641", weight: 0.17}
  - {name: 黄金,    source: sina_fut, code: AU0,      weight: 0.15, tracking_diff: 0.003}
```

### proxy：解决「好基金历史都太短」

低费率的指数基金普遍是近几年成立的。直接回测 `configs/default.yaml` 的公共窗口只有 **3.5 年**，
做 10 年期检验样本严重不足。所以每个资产可以额外声明一个长历史代理：

```yaml
  - name: 美股标普500
    source: fund
    code: "017641"          # 实盘买这个
    weight: 0.18
    proxy:                  # 回测用这个（同一标的，18.7 年历史）
      source: sina_us
      code: ".INX"
      dividend: 0.019       # 价格指数缺失的股息，补回
      fx: USDCNY            # 折算人民币，含汇率影响
      annual_fee: 0.0065    # 指数不含费用，扣掉
```

加 `--proxy` 即在长历史上跑。**两个口径的结果不可混用于同一结论。**

三个校正字段是把「代理」还原成「可买产品」的关键：

| 字段 | 用途 | 例子 |
|---|---|---|
| `dividend` | 价格指数缺失的股息 | 标普 1.9%、港股红利 4% |
| `annual_fee` | 指数不含基金费用 | A股 0.20%、QDII 0.65% |
| `tracking_diff` | 代理与实际产品的差 | 沪金 AU0 vs 黄金ETF：0.30%（实测校准） |

## 支持的赛道

| 赛道 | `source` | 说明 |
|---|---|---|
| 场外基金（全品类） | `fund` | 天天基金，27,790 只，复权净值已含分红与费用 |
| A股/港股通指数 | `csindex` | 中证官网，`H` 开头为**全收益**，可回溯到 2004 |
| 美股指数 | `sina_us` | `.INX` `.IXIC` `.DJI`，2004 起 |
| 港股指数 | `sina_hk` | `HSI` `HSCEI` `HSTECH` |
| 商品 | `sina_fut` | `AU0` 沪金(2008起) `AG0` 银 `CU0` 铜(2005起) `SC0` 原油 |
| 其他任意 | `akshare` | 逃生舱，直接调 akshare 任意接口 |

`configs/examples/` 下有商品、全球股票、全天候、A股多风格、指数长历史五个现成示例。

**新增一个赛道** = 写一个 `Source` 子类并 `@register`，其余（回测/检验/报告）全部自动可用：

```python
from dca.sources import Source, register, http_get

@register
class MySource(Source):
    key = "my"
    label = "我的数据源"
    def _fetch(self, code):
        ...  # 返回 DataFrame[date, px]
```

## 数据与礼仪

**本仓库不包含任何行情数据**，只包含取数代码。数据版权归各来源所有，请自行抓取，不要重分发。

默认每次网络请求间隔 **3 秒**（`DCA_MIN_GAP` 可调，但请勿调低）。
中证指数官网限流严格，务必依赖本地缓存。

## 一个真实的数据陷阱

筛查中发现中证 `H20269`「红利低波100全收益」相对其价格指数的隐含股息率高达 **6.06%/年**
（正常红利指数约 3.9%），与同系列不自洽，判定为口径不匹配。
**若误用该序列，会得出「红利低波年化 16.7%、超过纳斯达克」的错误结论。**

用价格指数与全收益指数反推隐含股息率来交叉校验，是接入任何新指数前都该做的一步。

## 目录

```
dca/
  sources/     数据源（可插拔）
  portfolio.py 组合定义、取数、对齐、口径校正
  engine.py    定投引擎（IRR / 滚动窗口 / 再平衡 / 递增 / 逆势加码）
  analysis/    起点敏感性、全周期矩阵、样本外、扰动、Bootstrap、蒙特卡洛
  cli.py       命令行
configs/       组合配置与各赛道示例
tests/         自检（IRR 精度、费率方向、窗口切片…）
archive/       最初的一次性研究脚本，仅作留档
```

## 免责声明

**本项目是历史数据的回测工具与研究记录，不构成投资建议，也不是任何形式的投资顾问服务。**

配置文件中出现的基金代码，是脚本按「同标的下年费率最低 + 规模达标 + 成立满一年」规则筛出的
**示例输出**，不是推荐。任何组合的实际结果取决于何时开始、能否坚持，以及未来真实发生了什么。

回测有其固有局限：滚动窗口样本高度重叠、指数基金存在生存者偏差、
历史收益率（尤其是债券与美股）大概率不可持续。
使用前请阅读 `docs/limitations.md`。请根据自身情况判断，必要时咨询有资质的投资顾问。

## License

MIT
