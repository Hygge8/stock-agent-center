# Stock Agent Center

AI 股票研究调度中心。当前版本是 **单仓库部署、三服务内置版**：只需要部署 `stock-agent-center`，Docker Compose 会自动把 `daily_stock_analysis` 和 `UZI-Skill` 一起作为内部服务启动。

```text
stock-agent-center
        |
        | 中控调度 / 规则判断 / 去重 / 统一入口
        |
        +---- embedded daily_stock_analysis
        |          股票池扫描 / 日报 / 发现机会
        |
        +---- embedded UZI-Skill
                   单票深度研究 / HTML 报告
```

## 当前版本：v0.3 单仓库三服务版

现在不需要分别部署：

```text
daily_stock_analysis
UZI-Skill
stock-agent-center
```

只需要部署：

```text
stock-agent-center
```

Docker 会自动启动：

```text
stock-agent-center          中控 Web / 规则调度 / 统一入口
stock-agent-daily-server    内置 daily_stock_analysis Web 服务
stock-agent-daily-analyzer  内置 daily_stock_analysis 定时分析服务
stock-agent-uzi-server      内置 UZI-Skill Web / HTML 深度报告
```

## 已实现能力

- FastAPI Web/API 入口
- SQLite 数据库
- 内置 `daily_stock_analysis` 服务
- 内置 `UZI-Skill` 服务
- 内置轻量股票池扫描器，作为 daily 的快速补充
- 扫描结果评分、排序、生成候选股票
- 规则引擎：score >= 85 进入 deep，score >= 70 进入 medium
- 自动调用内置 UZI-Skill Web API
- 保存候选股票和 UZI 报告任务记录
- 钉钉统一通知出口
- Docker Compose 一键启动全部内部服务

## 项目结构

```text
stock-agent-center
├── api
│   └── main.py
├── services
│   ├── stock_scanner.py
│   ├── daily_client.py
│   ├── uzi_client.py
│   ├── scheduler.py
│   ├── notifier.py
│   └── rule_engine.py
├── database
│   ├── database.py
│   └── models.py
├── config
│   └── settings.py
├── docker
│   ├── docker-compose.yml
│   └── Dockerfile.uzi
├── reports
├── requirements.txt
├── .env.example
└── README.md
```

## 快速启动

```bash
git clone https://github.com/Hygge8/stock-agent-center.git
cd stock-agent-center
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
```

Windows：

```cmd
cd /d "D:\项目\docker"
git clone https://github.com/Hygge8/stock-agent-center.git
cd /d "D:\项目\docker\stock-agent-center"
copy .env.example .env
docker compose -f docker/docker-compose.yml up -d --build
```

打开三个入口：

```text
中控入口：       http://localhost:9000
daily_stock：   http://localhost:8000
UZI-Skill：     http://localhost:8977
```

## 常用命令

查看状态：

```bash
docker compose -f docker/docker-compose.yml ps
```

查看中控日志：

```bash
docker compose -f docker/docker-compose.yml logs -f agent-center
```

查看 daily 日志：

```bash
docker compose -f docker/docker-compose.yml logs -f daily-server
docker compose -f docker/docker-compose.yml logs -f daily-analyzer
```

查看 UZI 日志：

```bash
docker compose -f docker/docker-compose.yml logs -f uzi-server
```

停止：

```bash
docker compose -f docker/docker-compose.yml down
```

## 配置

`.env` 示例：

```env
SERVER_PORT=9000

# 内置 daily_stock_analysis
DAILY_REPO_CONTEXT=https://github.com/Hygge8/daily_stock_analysis.git#fix/dingtalk-web-settings
DAILY_WEB_PORT=8000
DAILY_API_URL=http://daily-server:8000
ENABLE_DAILY_SYNC=true

# 内置 UZI-Skill
UZI_REPO=https://github.com/Hygge8/UZI-Skill.git
UZI_REF=feature/uzi-web-docker
UZI_WEB_PORT=8977
UZI_API_URL=http://uzi-server:8977
UZI_DEFAULT_DEPTH=deep

# 股票池
STOCK_POOL=VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ

# 规则
DEEP_SCORE_THRESHOLD=85
MEDIUM_SCORE_THRESHOLD=70

# 钉钉
DINGTALK_WEBHOOK_URL=
DINGTALK_SECRET=
ENABLE_DINGTALK_NOTIFY=false
```

## Web 使用

### 1. 中控入口

```text
http://localhost:9000
```

用于：

```text
股票池扫描
候选股评分
按规则进入 UZI
查看候选记录
查看 UZI 任务记录
```

### 2. daily_stock_analysis 入口

```text
http://localhost:8000
```

用于：

```text
完整 daily_stock_analysis WebUI
自选股扫描
每日分析
市场复盘
通知配置
```

### 3. UZI-Skill 入口

```text
http://localhost:8977
```

用于：

```text
单票深度研究
批量 UZI 分析
HTML 深度报告
历史报告查看
```

## 中控扫描流程

输入：

```text
VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ
```

点击：

```text
扫描股票池并调度 UZI
```

流程：

```text
拉取行情
  ↓
计算动量 / 趋势 / 量能 / 波动
  ↓
生成 0-100 分
  ↓
score >= 85 自动 deep
score >= 70 自动 medium
  ↓
调用 UZI 生成 HTML 深度报告
```

## API

### GET /health

健康检查。

### POST /api/scan

扫描股票池并按规则进入 UZI。

请求：

```json
{
  "symbols": "VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ",
  "auto_submit": true,
  "depth": null
}
```

### POST /api/analyze

手动提交股票给 UZI-Skill。

请求：

```json
{
  "symbol": "NVDA",
  "depth": "deep",
  "score": 88,
  "signal": "重点关注"
}
```

### GET /api/candidates

查看候选股票记录。

### GET /api/reports

查看 UZI 报告任务记录。

## 数据目录

```text
database/       stock-agent-center SQLite 数据库
reports/        stock-agent-center 记录目录
logs/           stock-agent-center 日志

daily-data/     daily_stock_analysis 数据库和运行数据
daily-reports/  daily_stock_analysis 报告
daily-logs/     daily_stock_analysis 日志

uzi-data/       UZI 运行数据
uzi-reports/    UZI HTML 报告
uzi-logs/       UZI 日志
uzi-cache/      UZI 缓存
```

## 与原两个项目的关系

```text
daily_stock_analysis = 完整内置，作为股票池/日报/市场复盘系统
UZI-Skill            = 完整内置，作为单票深度研究引擎
stock-agent-center   = 统一部署入口、调度中控、规则判断、统一推送
```

## 注意

`daily_stock_analysis` 的 Docker 构建使用：

```text
https://github.com/Hygge8/daily_stock_analysis.git#fix/dingtalk-web-settings
```

这样会包含你之前补的钉钉 WebUI 配置能力。

## 投资风险说明

本项目只用于学习、研究和复盘辅助，不构成投资建议。
