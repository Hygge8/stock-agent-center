# Stock Agent Center

AI 股票研究调度中心。当前版本改成 **单项目部署模式**：只需要部署 `stock-agent-center`，Docker Compose 会同时启动内置的 `uzi-server`，并由 `stock-agent-center` 自己完成轻量股票池扫描。

```text
stock-agent-center
        |
        | 内置股票池扫描 / 评分 / 候选筛选
        v
候选股票池
        |
        | 规则判断 / 去重 / 调度
        v
内置 UZI-Skill Web
        |
        | 单票深度研究 / HTML 报告
        v
钉钉推送
```

## 当前版本：v0.2 单项目部署版

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
stock-agent-center       中控 Web / 股票池扫描 / 规则调度
stock-agent-uzi-server   内置 UZI-Skill Web / HTML 深度报告
```

## 已实现能力

- FastAPI Web/API 入口
- SQLite 数据库
- 内置轻量股票池扫描，替代 daily_stock_analysis 的基础发现能力
- 扫描结果评分、排序、生成候选股票
- 规则引擎：score >= 85 进入 deep，score >= 70 进入 medium
- 自动调用内置 UZI-Skill Web API
- 保存候选股票和 UZI 报告任务记录
- 钉钉统一通知出口
- Docker Compose 一键启动两个内部服务
- 外部 daily_stock_analysis 接入预留

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

打开：

```text
http://localhost:9000
```

UZI 内部服务也会暴露：

```text
http://localhost:8977
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

# 内置 UZI 服务，单项目部署时无需修改
UZI_API_URL=http://uzi-server:8977
UZI_DEFAULT_DEPTH=deep

# 股票池
STOCK_POOL=VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ
SCAN_PERIOD=3mo
SCAN_INTERVAL=1d
AUTO_SUBMIT_SCAN_RESULTS=true

# 规则
DEEP_SCORE_THRESHOLD=85
MEDIUM_SCORE_THRESHOLD=70

# 钉钉
DINGTALK_WEBHOOK_URL=
DINGTALK_SECRET=
ENABLE_DINGTALK_NOTIFY=false
```

## Web 使用

页面提供两个入口：

### 股票池扫描

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

### 手动提交 UZI

输入单只股票，例如：

```text
NVDA
```

选择：

```text
deep
```

提交后会调用内置 UZI。

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
database/      SQLite 数据库
reports/       stock-agent-center 记录目录
logs/          stock-agent-center 日志
uzi-data/      内置 UZI 运行数据
uzi-reports/   内置 UZI HTML 报告
uzi-logs/      内置 UZI 日志
uzi-cache/     内置 UZI 缓存
```

## 与原两个项目的关系

```text
daily_stock_analysis = 股票池/日报系统，当前用内置轻量扫描替代基础能力
UZI-Skill            = 单票深度研究引擎，当前由 Docker 自动内置启动
stock-agent-center   = 统一部署入口、调度中控、规则判断、统一推送
```

以后如果想换回专业版 daily，也可以把 `ENABLE_DAILY_SYNC=true`，接入外部 daily_stock_analysis。

## 投资风险说明

本项目只用于学习、研究和复盘辅助，不构成投资建议。
