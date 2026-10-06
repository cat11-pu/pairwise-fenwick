# pairwise-fenwick

只依赖 Python 标准库的排行榜索引内核：分数档位与玩家都由调用方给出，
不使用真实时钟、线程、网络或随机数，同一串提交与退榜操作永远得到同样的榜单。

- `fenwick/core.py` — 内核：1 基树状数组（单点加减、前缀和、区间和、按升序序号定位），
  以及榜单（登记与改分、退榜、查分数、计数、区间统计、名次、按名次取人、取前若干名）。
- `tests/test_core.py` — 验收用例。

## 运行测试

在项目根目录执行：

```
python3 -m unittest discover -s tests -v
```

Windows 上如果没有 `python3`，可用：

```
python -m unittest discover -s tests -v
```
