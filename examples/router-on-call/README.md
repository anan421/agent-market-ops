# A股值班路由（router-on-call）

> 示例数据，不构成投资建议。Synthetic / public sample only. Not investment advice. No live trading.

自包含演示：用浏览器打开 [`index.html`](index.html) 即可。无构建步骤、无外部 CDN、无密钥。

## 模式

Vincent 的 A 股值班骨架（运维层，不是交易系统）：

| 角色 | 职责 |
|---|---|
| **Router** | 窄规则：先判定忽略还是交给专家。不报价、不下单。 |
| **TRIAGE** | 把入站事件分成噪声 / 待核。 |
| **FIXER** | 核对公开材料缺口（公告文本、线程、证伪窗）。 |
| **REVIEWER** | 复核「值不值得写成草稿」。 |
| **WRITER** | 起草值班说明。本示例日 **drafts=0**。 |
| **GUARD** | 没有自动发送、没有下单通道。出口只经过 **YOU**。 |

人是唯一审批门。Router 与四位专家都不能绕过 GUARD。

## 示例日数字（illustrative）

下列计数按 **2026-10-23** 这一天的公开合成样例风格填写，仅用于说明漏斗，不是实盘统计。

| 字段 | 值 |
|---|---|
| `events_in` | **151** |
| `ignored` | **142**（约 **94%**） |
| `handled` | **9** |
| `drafts` | **0** |
| 决策 | **今天不做** |

入站源（合成拆分，加总 = 151）：

- X预窗口 88
- 公告 32
- 证伪 15
- GitHub 16

灰柱是忽略流量，蓝柱是处理流量。页面上**没有**持仓、买卖信号或盈亏。

## 怎么看

```bash
# 从仓库根目录
python3 -m http.server 8765
# 打开 http://127.0.0.1:8765/examples/router-on-call/
```

或直接用浏览器打开 `examples/router-on-call/index.html`。

动画：Router 圆圈脉冲、事件粒子从左侧源流向中枢（多数下沉为 ignored，少数流向专家卡）。

## 许可与红线

与仓库其余部分一样，MIT。请勿把本目录当成实盘控制台：

- 不要写入真实持仓、信号、盈亏或券商凭证
- 不要把示例日数字说成业绩
- 简报锁定句式仍是仓库的 「今天不做」 规则
