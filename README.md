# Sequoia-X: 王者回归 | The King Returns

> A 股量化选股系统 V2 | A-Share Quantitative Stock Selection System V2

---

## 简介 | Introduction

Sequoia-X V2 是面向 A 股市场的量化选股系统，基于现代 Python 工程化标准从零重构。
系统以 OOP 架构、向量化计算和增量数据更新为核心设计原则，每日收盘后自动选股并推送至飞书群。

数据层使用 [baostock](http://baostock.com)（免费、无需注册、无限流）拉取历史及增量日 K 数据（后复权），
存储于本地 SQLite，彻底规避东方财富反爬问题。

---

## 三种运行模式

```bash
python main.py               # 日常模式：8进程增量补数据 + 跑策略 + 飞书推送（2~3分钟）
python main.py --backfill    # 回填模式：全市场历史K线一次性灌入（约12分钟）
python main.py web           # Web 仪表盘：可视化管理、配置飞书推送、浏览数据
```

---

## 内置策略 | Strategies

| 策略 | webhook_key | 说明 |
|---|---|---|
| **MaVolume** | `ma_volume` | 均线放量：5日均线上穿20日均线（金叉）且成交量放大1.5倍 |
| **TurtleTrade** | `turtle` | 海龟突破：20日新高 + 成交额过亿 + 阳线防诱多，按涨幅排序 |
| **HighTightFlag** | `flag` | 高位旗形：40日涨幅>60% + 10日窄幅震荡 + 缩量整理 |
| **LimitUpShakeout** | `shakeout` | 涨停洗盘：昨日涨停 + 今日阴线放量 + 不破涨停支撑 |
| **UptrendLimitDown** | `limit_down` | 上升趋势跌停：MA20>MA60 上升趋势 + 今日跌停 + 放量 |
| **RpsBreakout** | `rps` | RPS相对强度：120日涨幅排名前10% + 接近120日新高 |

---

## Web 仪表盘 | Web Dashboard

`python main.py web` 启动后访问 `http://localhost:8000`，提供以下功能：

### 策略总览（Dashboard）

- 6 个策略卡片，显示名称、描述、最新选股数量
- 一键运行任意策略，实时显示进度和结果
- 结果表格含雪球链接，点击直接跳转查看个股

### 飞书配置

- 可视化编辑默认 Webhook URL 和 6 个策略专属 Webhook
- 每个 URL 旁有「测试」按钮，一键验证连通性
- 配置自动保存到 `.env` 文件并实时生效

### 股票浏览

- 按代码模糊搜索，支持部分匹配（如输入 `600` 查找所有 600 开头的股票）
- 查看个股概览：最新收盘价、涨跌幅、数据范围
- K 线数据表：支持 30/60/120/250 天切换

### 系统监控

- 数据库大小、数据总行数、股票数量、最新同步日期
- 运行日志实时滚动显示（10 秒自动刷新）
- **同步数据**：一键增量拉取今日数据（2~3 分钟）
- **回填历史**：一键回填全市场历史 K 线（约 12 分钟）

### API 文档

FastAPI 自动生成 Swagger 文档：`http://localhost:8000/docs`

### Web 命令参数

```bash
python main.py web                   # 默认 0.0.0.0:8000
python main.py web --port 9000       # 自定义端口
python main.py web --host 127.0.0.1  # 仅本机访问
python main.py web --reload          # 开发模式（代码变更自动重载）
```

---

## 快速开始 | Quick Start

### 环境要求

- Python >= 3.10

### 1. 安装依赖

```bash
# 推荐使用 uv（快速包管理器）
uv sync

# 或者 pip
pip install .
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写飞书 Webhook URL
```

### 3. 首次回填历史数据

```bash
python main.py --backfill
```

约 12 分钟完成 ~5200 只 A 股历史后复权日 K 数据回填。

也可以启动 Web 仪表盘后在「系统监控」页面点击「回填历史」按钮。

### 4. 日常运行

```bash
python main.py
```

建议配合 crontab 每个交易日收盘后自动执行：

```cron
15 19 * * 1-5 cd /root/Sequoia-X && .venv/bin/python main.py >> log.txt 2>&1
```

### 5. 启动 Web 仪表盘（可选）

```bash
python main.py web
# 浏览器访问 http://localhost:8000
```

---

## 目录结构 | Project Structure

```
Sequoia-X/
├── main.py                        # 入口：argparse 分发日常/回填/Web 模式
├── pyproject.toml                 # 依赖声明 + ruff/pytest 配置
├── .env.example                   # 环境变量模板
├── data/                          # SQLite 数据库（运行时生成，不入 git）
├── sequoia_x/
│   ├── core/
│   │   ├── config.py              # Pydantic-settings 配置管理
│   │   └── logger.py              # rich 结构化日志
│   ├── data/
│   │   └── engine.py              # 数据引擎（baostock 回填 + 增量同步 + SQLite）
│   ├── strategy/
│   │   ├── base.py                # 策略抽象基类
│   │   ├── turtle_trade.py        # 海龟交易策略
│   │   ├── ma_volume.py           # 均线放量策略
│   │   ├── high_tight_flag.py     # 高窄旗形策略
│   │   ├── limit_up_shakeout.py   # 涨停洗盘策略
│   │   ├── uptrend_limit_down.py  # 上升跌停策略
│   │   └── rps_breakout.py        # RPS 突破策略
│   ├── notify/
│   │   └── feishu.py              # 飞书 Webhook 推送
│   └── web/                       # Web 仪表盘
│       ├── app.py                 # FastAPI 应用工厂
│       ├── services.py            # 服务层（策略执行、数据查询、系统监控）
│       ├── env_writer.py          # .env 文件安全读写
│       ├── routes/
│       │   ├── pages.py           # HTML 页面路由
│       │   └── api.py             # JSON API 路由
│       ├── templates/             # Jinja2 模板
│       │   ├── base.html          # Bootstrap 5 基础布局
│       │   ├── index.html         # 策略总览 Dashboard
│       │   ├── strategy_detail.html
│       │   ├── config.html        # 飞书配置编辑
│       │   ├── stock_browser.html # 股票数据浏览
│       │   └── system.html        # 系统监控
│       └── static/
│           ├── css/custom.css
│           └── js/app.js
└── tests/                         # 属性测试（hypothesis）
```

---

## 数据说明

- **数据源**：[baostock](http://baostock.com)（免费、无需注册、无限流）
- **复权方式**：后复权（hfq）— 历史价格不变，适合增量存储，避免除权导致数据错乱
- **存储**：本地 SQLite（`data/sequoia_v2.db`），可直接拷贝到其他机器使用
- **日常增量**：8 进程并行通过 baostock 拉取，2~3 分钟完成全市场更新
- **Web 并发**：SQLite 启用 WAL 模式，Web 读取与 CLI 写入互不阻塞

---

## 技术栈 | Tech Stack

| 层 | 技术 |
|---|---|
| 语言 | Python >= 3.10 |
| 数据源 | baostock |
| 存储 | SQLite |
| 数据处理 | pandas（向量化） |
| 配置 | pydantic-settings + python-dotenv |
| 通知 | requests（飞书 Webhook） |
| Web | FastAPI + Jinja2 + Bootstrap 5 |
| 日志 | rich |
| 测试 | pytest + hypothesis |
| 包管理 | uv |

---

## 许可证 | License

MIT
