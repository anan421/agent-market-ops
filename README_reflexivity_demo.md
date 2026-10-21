# reflexivity_demo（反射性 / 偏差拐点 示例）

> 示例数据，不构成建议。Synthetic data only, not advice.

## 30 秒上手 / 30-second quickstart

```bash
python3 -m pipeline.reflexivity_demo --market us --seed 42
# --market: cn_a | hk | us | crypto | futures | fx | demo
```

Sample output (real, `--market us`):

```text
示例数据，不构成建议 / synthetic demo data, not advice
市场 market: us (美股) | 货币 currency: USD | 时区 tz: America/New_York

[循环强度 loop strength] 峰值 lag=+1, corr=0.106
  价格领先叙事 1 天：价格先动，大家再去找故事 / price leads narrative by 1d: price moves, then the story follows.

[最近 3 个背离点 latest 3 divergences]
  2000-08-17 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.
  2000-08-19 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.
  2000-08-20 price_low_narrative_rising: 价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.

[示例登记论点 example registered theses]
  1) 价格阈值 price threshold: 若 DEMO-IDX 收盘 >= 129.06 于 2000-09-08 前则错 -> 未被证伪 / not falsified
     收盘没碰到阈值，论点暂时活着 / close never touched the threshold, thesis survives for now.
  2) 相对 relative: 若等权 DEMO-BASKET-A+B 在 2000-07-11~2000-09-08 跑赢 DEMO-BENCH 则错 -> 被证伪 / falsified
     篮子跑赢了基准（未复权收盘），论点错了 / basket beat benchmark, thesis is wrong.

未被证伪 ≠ 我对了 / not falsified is not proof
```

登记你自己的论点 / register your own thesis (run from repo root):

```python
import datetime as dt
from pipeline import reflexivity_demo as rd
d = rd.generate_demo_data(seed=42, market_key="demo")
t = rd.PriceThresholdThesis("DEMO-IDX", 110.0, dt.date(2000, 6, 1))  # 错的标准: 收盘 >= 110
print(rd.evaluate(t, d))  # -> 'falsified' 或 'not_falsified'，永远不会是 'correct'
# prints: falsified
```

## 说明 / Details

- 虚构序列 / fictional series: DEMO-IDX, DEMO-NARRATIVE, DEMO-BASKET-A/B, DEMO-BENCH, seeded.
- 每条序列带必填字段 `market`（cn_a/hk/us/crypto/futures/fx/demo）、`currency`、`tz`；逻辑只读字段，不从代码猜市场。中文标签只用于报告显示。Each series carries required market/currency/tz; nothing is guessed or hard-coded.
- `rolling_corr`, `lead_lag`: 量反馈环 / measure the loop. `divergence_points`: 候选拐点 / candidate turning points.
- `PriceThresholdThesis`, `RelativeThesis` (frozen) + `evaluate`: only falsified / not_falsified. Relative uses unadjusted closes.

Test: `python3 -m pytest -q tests`
