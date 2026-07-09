"""FastAPI entrypoint for stock-agent-center."""
from __future__ import annotations

import json
from typing import Any, Literal

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.settings import settings
from database.database import get_db, init_db
from database.models import StockCandidate, UziReport
from services.notifier import DingTalkNotifier
from services.rule_engine import decide
from services.scheduler import start_scheduler
from services.uzi_client import UziClient

app = FastAPI(title="Stock Agent Center", version="0.1.0")
notifier = DingTalkNotifier()


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=64)
    depth: Literal["lite", "medium", "deep"] | None = None
    score: float | None = None
    signal: str | None = None
    source: str = "manual"
    notify: bool = False
    no_resume: bool = False


class CandidateItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=64)
    score: float | None = None
    signal: str | None = None


class CandidateBatchRequest(BaseModel):
    source: str = "daily_stock_analysis"
    items: list[CandidateItem]
    auto_submit: bool = True


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    start_scheduler()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Stock Agent Center</title>
  <style>
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f6f7fb;color:#111827}
    header{background:#111827;color:white;padding:22px 28px}main{max-width:1120px;margin:24px auto;padding:0 16px}
    .grid{display:grid;grid-template-columns:380px 1fr;gap:16px}.card{background:white;border-radius:14px;padding:18px;box-shadow:0 10px 30px rgba(15,23,42,.08)}
    input,select,button{box-sizing:border-box;width:100%;border:1px solid #d1d5db;border-radius:10px;padding:11px 12px;font-size:15px}button{background:#2563eb;color:white;border:0;font-weight:700;margin-top:12px;cursor:pointer}
    label{display:block;margin:12px 0 6px;font-weight:700}.hint{color:#6b7280;font-size:13px;line-height:1.6}pre{background:#0f172a;color:#d1d5db;border-radius:10px;padding:12px;white-space:pre-wrap;overflow:auto;max-height:400px}
    table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:9px;text-align:left;font-size:14px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  </style>
</head>
<body>
<header><h1>Stock Agent Center</h1><p>连接 daily_stock_analysis 和 UZI-Skill 的股票研究调度中枢</p></header>
<main>
  <div class="grid">
    <section class="card">
      <h2>手动提交 UZI 深度研究</h2>
      <label>股票代码</label><input id="symbol" value="NVDA" placeholder="NVDA / TSLA / QQQ" />
      <label>深度</label><select id="depth"><option value="deep">deep</option><option value="medium">medium</option><option value="lite">lite</option></select>
      <label>评分</label><input id="score" value="88" />
      <label>信号</label><input id="signal" value="重点关注" />
      <button onclick="analyze()">提交分析</button>
      <p class="hint">v0.1：先打通 agent-center → UZI-Skill → SQLite 记录。</p>
    </section>
    <section class="card">
      <h2>结果</h2><pre id="result">等待操作...</pre>
    </section>
  </div>
  <section class="card" style="margin-top:16px"><h2>最近报告</h2><div id="reports">加载中...</div></section>
</main>
<script>
async function analyze(){
  const payload={symbol:document.getElementById('symbol').value.trim(),depth:document.getElementById('depth').value,score:Number(document.getElementById('score').value),signal:document.getElementById('signal').value};
  const res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await res.json();document.getElementById('result').textContent=JSON.stringify(data,null,2);loadReports();
}
async function loadReports(){
  const res=await fetch('/api/reports');const data=await res.json();
  if(!data.length){document.getElementById('reports').innerHTML='暂无报告记录';return;}
  document.getElementById('reports').innerHTML='<table><thead><tr><th>标的</th><th>深度</th><th>状态</th><th>任务</th></tr></thead><tbody>'+data.map(r=>`<tr><td class="mono">${r.symbol}</td><td>${r.depth}</td><td>${r.status}</td><td class="mono">${r.job_id||'-'}</td></tr>`).join('')+'</tbody></table>';
}
loadReports();
</script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "stock-agent-center",
        "version": "0.1.0",
        "uzi_api_url": settings.uzi_api_url,
        "daily_api_url": settings.daily_api_url,
        "dingtalk_enabled": settings.enable_dingtalk_notify,
    }


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    symbol = request.symbol.strip().upper()
    decision = decide(request.score, request.signal)
    depth = request.depth or decision.depth or settings.uzi_default_depth

    candidate = StockCandidate(
        symbol=symbol,
        score=request.score,
        signal=request.signal,
        source=request.source,
        decision=decision.action,
        depth=depth,
        raw_payload=request.model_dump_json(),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    if decision.action == "ignore" and request.depth is None:
        return {
            "ok": True,
            "symbol": symbol,
            "decision": decision.action,
            "reason": decision.reason,
            "message": "candidate saved, ignored by rule engine",
        }

    client = UziClient()
    try:
        uzi_response = client.analyze(symbol=symbol, depth=depth, notify=False, no_resume=request.no_resume)
    except Exception as exc:
        report = UziReport(
            symbol=symbol,
            depth=depth,
            status="submit_failed",
            source=request.source,
            raw_response=json.dumps({"error": str(exc)}, ensure_ascii=False),
        )
        db.add(report)
        db.commit()
        raise HTTPException(status_code=502, detail=f"UZI submit failed: {exc}") from exc

    job_id = client.extract_job_id(uzi_response)
    report_url = client.extract_report_url(uzi_response)
    status = client.extract_status(uzi_response)

    report = UziReport(
        symbol=symbol,
        job_id=job_id,
        depth=depth,
        report_url=report_url,
        status=status,
        source=request.source,
        raw_response=json.dumps(uzi_response, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if request.notify:
        notifier.notify_candidate_submitted(symbol=symbol, score=request.score, depth=depth, job_id=job_id)

    return {
        "ok": True,
        "symbol": symbol,
        "depth": depth,
        "decision": decision.action,
        "reason": decision.reason,
        "uzi_job_id": job_id,
        "uzi_status": status,
        "report_url": report_url,
        "candidate_id": candidate.id,
        "report_id": report.id,
        "uzi_response": uzi_response,
    }


@app.post("/api/candidates")
def ingest_candidates(request: CandidateBatchRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    results = []
    for item in request.items:
        if request.auto_submit:
            result = analyze(
                AnalyzeRequest(
                    symbol=item.symbol,
                    score=item.score,
                    signal=item.signal,
                    source=request.source,
                ),
                db=db,
            )
            results.append(result)
        else:
            decision = decide(item.score, item.signal)
            candidate = StockCandidate(
                symbol=item.symbol.strip().upper(),
                score=item.score,
                signal=item.signal,
                source=request.source,
                decision=decision.action,
                depth=decision.depth,
                raw_payload=item.model_dump_json(),
            )
            db.add(candidate)
            db.commit()
            results.append({"symbol": candidate.symbol, "candidate_id": candidate.id, "decision": decision.action})
    return {"ok": True, "count": len(results), "results": results}


@app.get("/api/candidates")
def list_candidates(limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(StockCandidate).order_by(StockCandidate.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "score": row.score,
            "signal": row.signal,
            "source": row.source,
            "decision": row.decision,
            "depth": row.depth,
            "created_time": row.created_time.isoformat() if row.created_time else None,
        }
        for row in rows
    ]


@app.get("/api/reports")
def list_reports(limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(UziReport).order_by(UziReport.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "symbol": row.symbol,
            "job_id": row.job_id,
            "depth": row.depth,
            "report_url": row.report_url,
            "status": row.status,
            "source": row.source,
            "created_time": row.created_time.isoformat() if row.created_time else None,
        }
        for row in rows
    ]


if __name__ == "__main__":
    uvicorn.run("api.main:app", host=settings.server_host, port=settings.server_port, reload=False)
