# 贡献指南

## 最需要的三类贡献

### 1. 修复失效的数据源 ⭐

这是本项目**最高频的问题**。公开行情接口会毫无预警地变更或关闭——
开发期间东方财富的 `push2his` 接口就在中途失效了，中证指数官网会 IP 限流。

如果 `dca fetch` 报错，请开一个 issue（用 **数据源失效** 模板），或者直接改 `dca/sources/providers.py`。
判断是接口挂了还是限流：换个网络/等几十分钟再试，限流通常会自己恢复。

### 2. 新增数据源 / 赛道

加一个赛道 = 写一个 `Source` 子类。回测、检验、报告会自动支持，无需改动其他任何地方。

```python
# dca/sources/providers.py
from .base import Source, register, http_get

@register
class MySource(Source):
    key = "my"                    # yaml 里 source: my
    label = "我的数据源（一句话说明口径）"
    total_return = False          # 数据是否已含分红再投资

    def _fetch(self, code: str) -> pd.DataFrame:
        txt = http_get(f"https://example.com/api?code={code}")
        ...
        return df                 # 必须是 DataFrame[date, px]，px 用于算收益率
```

要求：

- **只返回 `date` 与 `px` 两列**，`px` 是可直接算收益率的序列（复权净值 / 全收益点位 / 连续合约价）
- **走 `http_get()`**，它统一了 UA、重试与节流。不要自己 `requests.get`
- **不要降低节流**（默认 3 秒）。对公开接口保持克制，这是本项目的底线
- 在 docstring 里写清 **code 的格式**和**数据口径**（是否含分红？什么币种？主力连续还是现货？）
- 在 README 的赛道表格里加一行

如果新源提供的是**价格指数**（不含分红），务必在文档里注明——使用者需要在配置里用 `dividend` 补回，
否则会系统性低估收益（A 股宽基低估 1.15–3.93 个百分点/年）。

### 3. 接入新指数前，先做口径校验

**这是本项目踩过的最大的坑。** 用价格指数与全收益指数反推隐含股息率：

```python
implied = cagr(total_return_index) - cagr(price_index)
```

正常范围：宽基 1–2%，红利类 3–5%。若明显偏离（我们遇到过 6.06%），说明两个序列不是同一编制口径，
**不要使用**。详见 `docs/limitations.md`。

## 开发流程

```bash
git clone <your-fork>
cd dca-backtest
pip install -e ".[dev,extra]"

pytest -q                    # 33 个测试，全部离线，应在 1 秒内跑完
ruff check dca tests         # lint
ruff format dca tests        # 格式化
```

### 测试要求

**新增的测试必须离线**——不发网络请求、不读 `data/` 缓存。
这是 CI 能够稳定绿的前提，也是本项目刻意的约束。

涉及数值计算的改动，请用**已知闭式解**校验，而不是用当前输出当基准。
`tests/test_engine.py::test_xirr_exact_equal_cashflow` 是范例——
正是这种测试抓出了 IRR 少贴现一期的 bug（该 bug 使所有收益率被系统性高估 0.06–0.33pp）。

### 提交前自检

- [ ] `pytest -q` 通过
- [ ] `ruff check dca tests` 通过
- [ ] 改了 `configs/` 或数据源？跑一次 `python -m dca run -c <config>` 确认能用
- [ ] 改了分析口径？在 PR 里说明**对已有结论的影响**（哪些数字会变、变多少）

## 不接受的改动

- **降低请求节流**或移除限流保护
- **把行情数据提交进仓库**（`data/` 已被忽略，请勿绕过）
- 把配置里的基金代码包装成"推荐"、"精选"或任何带收益承诺的表述
- 只改数字不说明口径的"优化结果"——本项目的立场是：
  **能被样本外检验推翻的优化，就不是优化**

## 一个提醒

这个项目的价值不在于"跑出更高的年化"，而在于**诚实地展示一个结论有多脆弱**。
如果你的 PR 让某个数字变好看了，请同时说明它在其他起点窗口、样本外、权重扰动下是否仍然成立。
