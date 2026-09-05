# archive — 原始研究记录

这里是本项目最初那次研究的一次性脚本，按时间顺序写成，**未经重构，不保证可直接运行**
（它们依赖当时的临时缓存文件名与写死的路径）。

保留它们是为了留档：`dca/` 里的框架就是从这些脚本提炼出来的，
两者的结论已交叉验证一致（见根目录 README 的对照表）。

日常使用请用 `dca/` 与 `configs/`，不要从这里开始。

- `research/probe*.py` —— 数据源可用性探测，记录了哪些接口能用、哪些已失效
- `research/run*.py`、`final*.py`、`windows.py`、`walkforward.py` 等 —— 各项分析的初版
- `research/selftest.py` —— 抓出 IRR 少贴现一期那个 bug 的自检脚本（现已并入 tests/）
