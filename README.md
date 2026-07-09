# Stock Agent Center

AI 股票研究调度中心，用来串联 `daily_stock_analysis` 和 `UZI-Skill`：

```text
daily_stock_analysis
        |
        | 股票池扫描 / 每日筛选 / 评分 / 趋势 / 热点
        v
候选股票池
        |
        | stock-agent-center 规则判断 / 去重 / 调度
        v
UZI-Skill
        |
        | 单票深度研究 / HTML 报告
        v
钉钉推送
```

## 当前版本：v0.1

第一版先完成中控系统最小闭环：

- FastAPI Web/API 入口
- SQLite 数据库
- 手动提交股票到 UZI-Skill
- 保存候选股票和 UZI 报告任务记录
- 钉钉统一通知出口
- Docker 一键启动
- daily_stock_analysis 接入预留

## 项目结构

```text
stock-agent-center
├── api
│   └── main.py
├── services
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
│   └── docker-compose.yml
├── reports
├── requirements.txt
├── .env.example
└── README.md
```

## 快速启动

复制配置：

```bash
cp .env.example .env
```

启动：

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

打开：

```text
http://localhost:9000
```

健康检查：

```bash
curl http://localhost:9000/health
```

## 调用 UZI-Skill

确保 UZI Web 已启动，例如：

```text
http://localhost:8977
```

`.env` 配置：

```env
UZI_API_URL=http://host.docker.internal:8977
```

提交分析：

```bash
curl -X POST http://localhost:9000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"NVDA","depth":"deep","score":88,"signal":"重点关注"}'
```

返回示例：

```json
{
  "ok": true,
  "symbol": "NVDA",
  "depth": "deep",
  "uzi_job_id": "20260709_...",
  "uzi_status": "queued"
}
```

## API

### GET /health

健康检查。

### GET /

简单 Web 管理页。

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

### POST /api/candidates

接收 daily_stock_analysis 或其他系统推送的候选股票列表，并按规则决定是否进入 UZI。

请求：

```json
{
  "source": "daily_stock_analysis",
  "items": [
    {"symbol":"NVDA", "score":88, "signal":"重点关注"},
    {"symbol":"TSLA", "score":82, "signal":"观察"}
  ]
}
```

### GET /api/candidates

查看候选股票记录。

### GET /api/reports

查看 UZI 报告任务记录。

## 规则引擎

第一版规则：

```text
score >= 85  -> UZI deep
score >= 70  -> UZI medium
其他         -> ignore
```

可通过 `.env` 调整：

```env
DEEP_SCORE_THRESHOLD=85
MEDIUM_SCORE_THRESHOLD=70
```

## 钉钉通知

配置：

```env
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=
```

建议钉钉机器人关键词设置为：

```text
股票
```

## 与两个项目的关系

```text
daily_stock_analysis = 股票池 / 日报系统 / 发现机会
UZI-Skill            = 单票深度研究引擎 / HTML 报告
stock-agent-center   = 中控调度 / 去重 / 规则 / 统一推送
```

## 版本规划

### v0.1

- UZI API 调用
- SQLite
- Docker
- 简单 Web 入口
- 候选股票接收接口

### v0.2

- 正式接入 daily_stock_analysis API
- 定时拉取 daily 结果
- 自动进入 UZI 深度研究

### v0.3

- Web 管理页面增强
- 历史报告中心
- 任务重试
- 去重策略

## 投资风险说明

本项目只用于学习、研究和复盘辅助，不构成投资建议。
