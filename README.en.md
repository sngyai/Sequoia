# Sequoia-X: The King Returns

> A-Share Quantitative Stock Selection System V2

**[中文](README.md) | English**

---

## Introduction

Sequoia-X V2 is a quantitative stock selection system for the China A-share market, rebuilt from scratch on modern Python engineering standards.
The system is designed around an OOP architecture, vectorized computation, and incremental data updates. It automatically screens stocks after each market close and pushes the results to a Feishu (Lark) group.

The data layer uses [baostock](http://baostock.com) (free, no registration, no rate limits) to fetch historical and incremental daily K-line data (backward-adjusted), stored in a local SQLite database — completely sidestepping the anti-scraping issues of East Money (Eastmoney).

---

## Two Run Modes

```bash
python main.py               # Daily mode: 8-process incremental data top-up + run strategies + Feishu push (2–3 min)
python main.py --backfill     # Backfill mode: one-time bulk load of full-market historical K-lines (~12 min)
```

---

## Built-in Strategies

| Strategy | Description |
|---|---|
| **TurtleTrade** | Turtle breakout: 20-day high + turnover over 100M + bullish candle to guard against bull traps, sorted by gain |
| **MaVolume** | Moving average + volume breakout |
| **HighTightFlag** | High and tight flag consolidation breakout |
| **LimitUpShakeout** | Limit-up shakeout pullback confirmation |
| **UptrendLimitDown** | Limit-down reversal (bullish engulfing) within an uptrend |
| **RpsBreakout** | O'Neil RPS relative-strength breakout |

---

## Quick Start

### Requirements

- Python >= 3.10

### 1. Install dependencies

```bash
# Recommended: uv (fast package manager)
uv sync

# Or pip
pip install .
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your Feishu Webhook URL
```

### 3. First-time historical backfill

```bash
python main.py --backfill
```

Completes the backfill of ~5,200 A-share stocks' backward-adjusted daily K-line history in about 12 minutes.

### 4. Daily run

```bash
python main.py
```

Recommended to run automatically via crontab after each trading day's close:

```cron
15 19 * * 1-5 cd /root/Sequoia-X && .venv/bin/python main.py >> log.txt 2>&1
```

---

## Project Structure

```
Sequoia-X/
├── main.py                      # Entry point: argparse dispatch for daily/backfill modes
├── pyproject.toml               # Dependency declarations + ruff/pytest config
├── .env.example                 # Environment variable template
├── data/                        # SQLite database (generated at runtime, not committed to git)
├── sequoia_x/
│   ├── core/
│   │   ├── config.py            # Pydantic-settings configuration management
│   │   └── logger.py            # rich structured logging
│   ├── data/
│   │   └── engine.py            # Data engine (baostock backfill + incremental sync + SQLite)
│   ├── strategy/
│   │   ├── base.py              # Strategy abstract base class
│   │   ├── turtle_trade.py      # Turtle trading strategy
│   │   ├── ma_volume.py         # Moving-average volume strategy
│   │   ├── high_tight_flag.py   # High tight flag strategy
│   │   ├── limit_up_shakeout.py # Limit-up shakeout strategy
│   │   ├── uptrend_limit_down.py # Uptrend limit-down strategy
│   │   └── rps_breakout.py      # RPS breakout strategy
│   └── notify/
│       └── feishu.py            # Feishu Webhook push
└── tests/                       # Property-based tests (hypothesis)
```

---

## Data Notes

- **Data source**: [baostock](http://baostock.com) (free, no registration, no rate limits)
- **Adjustment method**: Backward adjustment (hfq) — historical prices stay unchanged, which suits incremental storage and avoids data corruption from ex-rights/ex-dividend events
- **Storage**: Local SQLite (`data/sequoia_v2.db`), which can be copied directly to another machine
- **Daily increment**: 8 processes fetch in parallel via baostock, completing a full-market update in 2–3 minutes

---

## License

MIT
