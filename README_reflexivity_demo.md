# reflexivity_demo（反射性 / 偏差拐点 示例）

> 示例数据，不构成建议。Synthetic data only, not advice. Fictional series: DEMO-IDX, DEMO-NARRATIVE, DEMO-BASKET-A/B, DEMO-BENCH.

- `generate_demo_data(seed)`：固定种子生成带反馈环的合成价格与叙事序列 / seeded synthetic price+narrative with a feedback loop.
- `rolling_corr`, `lead_lag`：量反馈环 / measure the loop.
- `divergence_points`：价格新高而叙事动量走弱（或反之）标为候选拐点 / candidate turning points.
- `PriceThresholdThesis`, `RelativeThesis`（frozen，登记后不可改）+ `evaluate`：只返回 `falsified` / `not_falsified`，从不说"正确"。Price: wrong if close >= X by date D. Relative: wrong if equal-weight basket beats benchmark (unadjusted closes).

Run: `python -m pipeline.reflexivity_demo` · Test: `pytest tests/test_reflexivity_demo.py`
