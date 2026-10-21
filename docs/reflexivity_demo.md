# reflexivity_demo（反射性 / 偏差拐点 示例）

> 示例数据，不构成建议。Synthetic data only, not advice. Code: [pipeline/reflexivity_demo.py](../pipeline/reflexivity_demo.py) · Tests: [tests/test_reflexivity_demo.py](../tests/test_reflexivity_demo.py)

## 30 秒上手 / 30-second quickstart

需要仓库里的 `markets/` 适配层（#5），所有市场参数都从它读取。
Requires the repo's `markets/` adapter (#5); all market values are read from it.

```bash
python3 -m pipeline.reflexivity_demo --market us --seed 42
# --market 取自 markets.available()：cn_a | hk | us | crypto | futures | fx | demo
```

Sample output (real, `--market us`):

```text
示例数据，不构成建议 / synthetic demo data, not advice
市场 market: us | 货币 currency: USD | 时区 tz: America/New_York

[循环强度 loop strength] 峰值 lag=+1, corr=0.106
  价格领先叙事 1 天：价格先动，大家再去找故事 / price leads narrative by 1d.
  试了 11 个滞后，取绝对值最大；n≈248，SE≈1/√n=0.064，corr 约 1.7 个标准误，未过多重比较，不算信号 / tried 11 lags, took the max; no multiple-comparison adjustment, not a signal.

[最近 3 个背离点 latest 3 divergences]
  2000-08-17 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.
  2000-08-19 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.
  2000-08-20 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.

[示例登记论点 example registered theses] 登记日 registered_on=2000-07-10，数据截至 2000-09-08
  1) 价格阈值 price threshold（= 登记日收盘 × 1.05）: 若 DEMO-IDX 在 (2000-07-10, 2000-08-19] 收盘 >= 121.06 则错 -> 未被证伪 / not falsified
     到期前收盘没碰到阈值，论点暂时活着 / no close touched the threshold by the deadline, thesis survives for now.
  2) 相对 relative（窗口 = 登记日起 40 天）: 若等权 DEMO-BASKET-A+B 在 2000-07-10~2000-08-19 跑赢 DEMO-BENCH 则错 -> 未被证伪 / not falsified
     篮子没跑赢基准（未复权收盘），论点暂时活着 / basket did not beat benchmark, thesis survives for now.

未被证伪 ≠ 我对了 / not falsified is not proof
```

登记你自己的论点 / register your own thesis (run from repo root):

```python
import datetime as dt
from pipeline import reflexivity_demo as rd
d = rd.generate_demo_data(seed=42, market_key="demo")
t = rd.PriceThresholdThesis("DEMO-IDX", 110.0, deadline=dt.date(2000, 6, 1), registered_on=dt.date(2000, 3, 1))
print(rd.evaluate(t, d))  # 'falsified' / 'not_falsified' / 'pending'，永远不会是 'correct'
# prints: falsified
```

## 规则 / Rules

- 每条序列带必填 `market`/`currency`/`tz`，配置只来自 `markets.load(name)`；不从代码猜市场，模块里没有写死的市场列表。
- 论点必须带 `registered_on`；参数只能用登记日及之前的数据（示例：阈值 = 登记日收盘 × `PRICE_FACTOR`，窗口 = 登记日起 `HORIZON_DAYS` 天，常量在文件开头声明）。
- 评估只用登记日之后的数据：价格阈值看 `(registered_on, deadline]` 内任一收盘 >= 阈值；相对论点窗口起点不得早于登记日（否则报错），未复权收盘，等权篮子 > 基准则错。
- **真实使用时，`registered_on` 和全部参数必须由用户在拿到数据之前填写。** demo 里「数据末尾前 60 天登记」只是为了让示例能复现，它只用到数据长度，不用登记后的价格。 / In real use, set `registered_on` and all parameters before seeing the data; the demo's 60-days-before-end rule exists only for reproducibility.
- 状态只有三种：`falsified` 被证伪 / `not_falsified` 未被证伪 / `pending` 未到期（到期日晚于最后数据日）。
- Lead-lag 报告写明试了多少个滞后、n、SE≈1/√n；未做多重比较校正，不算信号。
- 背离检测只用 t 及之前的数据（有因果性测试）。

Test: `python3 -m pytest -q tests`（直接使用仓库的 `markets/` 包 / uses the real repo `markets/` package）
