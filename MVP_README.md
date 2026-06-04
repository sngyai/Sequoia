# A股 MVP 使用说明

本说明只覆盖本地 MVP 封装脚本，不改变 Sequoia-X 原策略逻辑。

## 从干净仓库复现

```bash
git clone <repo-url>
cd Sequoia-X
uv sync
uv run python scripts/run_mvp_screen.py --backfill-only
uv run python scripts/run_mvp_screen.py
```

`data/*.db` 和 `outputs/` 是本地运行产物，不提交到 Git。

## 每日运行

```bash
uv run python scripts/run_mvp_screen.py
```

生成：

- `outputs/daily_candidates.csv`：当天候选池
- `outputs/signal_tracking.csv`：复盘跟踪表
- `outputs/exit_log.csv`：手工交易记录表
- `outputs/data_health.csv`：本地行情数据健康检查
- `outputs/exit_alerts.csv`：持仓退出提醒
- `outputs/daily_report.md`：每日看板

## 补数据

```bash
uv run python scripts/run_mvp_screen.py --backfill-only
```

只补缺失 K 线并刷新 `data_health.csv`，不跑策略。

## 复盘回填

```bash
uv run python scripts/backfill_tracking.py
```

在未来交易日数据已存在时，回填：

- `close_t1 / close_t3 / close_t5`
- `return_t1 / return_t3 / return_t5`
- `max_drawdown_5d`

同一命令会刷新 `outputs/review_summary.csv`。

## 每天怎么看

优先看 `outputs/daily_report.md`。

主候选条件：

- `RpsBreakout` 和 `TurtleTrade` 同时命中
- 一手成本 `<= 4500`
- 非 ST
- 沪深主板账户可交易
- 基础面硬过滤未失败

观察池不能自动当作交易候选。

## 手工交易记录

如果实际买入，在 `outputs/exit_log.csv` 追加：

- `buy_date`
- `code`
- `name`
- `buy_price`
- `buy_reason`
- `initial_stop_price`

`initial_stop_price = buy_price * 0.94`。

卖出后补：

- `exit_date`
- `exit_price`
- `exit_reason`
- `holding_days`
- `return_pct`

## 当前硬过滤

- `st_stock`
- `low_price_high_risk`
- `watch_only`
- `not_affordable`
- `no_star_market_access`
- `no_chinext_access`
- `no_bse_access`
- `roe_negative`
- `debt_ratio_high`

AKShare 当前网络不可用时，会自动使用 baostock 财报数据兜底。
