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
from services.stock_scanner import StockScanner
from services.uzi_client import UziClient

app = FastAPI(title="Stock Agent Center", version="0.2.0")
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
    source: str = "stock_scanner"
    items: list[CandidateItem]
    auto_submit: bool = True


class ScanRequest(BaseModel):
    symbols: str | None = None
    auto_submit: bool = True
    depth: Literal["lite", "medium", "deep"] | None = None
    notify: bool = False


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
    header{background:#111827;color:white;padding:22px 28px}main{max-width:1180px;margin:24px auto;padding:0 16px}
    .grid{display:grid;grid-template-columns:390px 1fr;gap:16px}.stack{display:grid;gap:16px}.card{background:white;border-radius:14px;padding:18px;box-shadow:0 10px 30px rgba(15,23,42,.08)}
    input,select,textarea,button{box-sizing:border-box;width:100%;border:1px solid #d1d5db;border-radius:10px;padding:11px 12px;font-size:15px}textarea{min-height:92px}button{background:#2563eb;color:white;border:0;font-weight:700;margin-top:12px;cursor:pointer}.secondary{background:#475569}
    label{display:block;margin:12px 0 6px;font-weight:700}.hint{color:#6b7280;font-size:13px;line-height:1.6}pre{background:#0f172a;color:#d1d5db;border-radius:10px;padding:12px;white-space:pre-wrap;overflow:auto;max-height:460px}
    table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #e5e7eb;padding:9px;text-align:left;font-size:14px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.ok{color:#166534}.bad{color:#b91c1c}
    @media(max-width:900px){.grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
<header><h1>Stock Agent Center</h1><p>一个项目部署：内置股票池扫描 + 内置 UZI 深度报告 + 统一调度</p></header>
<main>
  <div class="grid">
    <div class="stack">
      <section class="card">
        <h2>股票池扫描</h2>
        <label>股票池</label>
        <textarea id="scanSymbols">VGT,SPCX,DRAM,QLD,TQQQ,NVDA,TSLA,QQQM,QQQ</textarea>
        <label>进入UZI深度</label>
        <select id="scanDepth"><option value="">按规则自动</option><option value="deep">deep</option><option value="medium">medium</option><option value="lite">lite</option></select>
        <label><input id="scanAuto" type="checkbox" checked /> 扫描后自动提交 UZI</label>
        <button onclick="scanPool()">扫描股票池并调度 UZI</button>
        <p class="hint">现在不需要单独部署 daily_stock_analysis；这里内置轻量扫描发现机会。</p>
      </section>
      <section class="card">
        <h2>手动提交 UZI 深度研究</h2>
        <label>股票代码</label><input id="symbol" value="NVDA" placeholder="NVDA / TSLA / QQQ" />
        <label>深度</label><select id="depth"><option value="deep">deep</option><option value="medium">medium</option><option value="lite">lite</option></select>
        <label>评分</label><input id="score" value="88" />
        <label>信号</label><input id="signal" value="重点关注" />
        <button class="secondary" onclick="analyze()">手动提交分析</button>
      </section>
    </div>
    <section class="card">
      <h2>结果</h2><pre id="result">等待操作...</pre>
    </section>
  </div>
  <section class="card" style="margin-top:16px"><h2>最近候选</h2><div id="candidates">加载中...</div></section>
  <section class="card" style="margin-top:16px"><h2>最近报告任务</h2><div id="reports">加载中...</div></section>
</main>
<script>
async function analyze(){
  const payload={symbol:document.getElementById('symbol').value.trim(),depth:document.getElementById('depth').value,score:Number(document.getElementById('score').value),signal:document.getElementById('signal').value};
  const res=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await res.json();document.getElementById('result').textContent=JSON.stringify(data,null,2);loadAll();
}
async function scanPool(){
  const payload={symbols:document.getElementById('scanSymbols').value,auto_submit:document.getElementById('scanAuto').checked,depth:document.getElementById('scanDepth').value||null};
  document.getElementById('result').textContent='扫描中，首次拉行情可能需要几十秒...';
  const res=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await res.json();document.getElementById('result').textContent=JSON.stringify(data,null,2);loadAll();
}
function table(rows, cols){if(!rows.length)return '暂无记录';return '<table><thead><tr>'+cols.map(c=>`<th>${c[0]}</th>`).join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>`<td class="${c[2]||''}">${r[c[1]]??'-'}</td>`).join('')+'</tr>').join('')+'</tbody></table>'}
async function loadAll(){
  let res=await fetch('/api/candidates');let cs=await res.json();document.getElementById('candidates').innerHTML=table(cs,[['标的','symbol','mono'],['评分','score'],['信号','signal'],['决策','decision'],['深度','depth']]);
  res=await fetch('/api/reports');let rs=await res.json();document.getElementById('reports').innerHTML=table(rs,[['标的','symbol','mono'],['深度','depth'],['状态','status'],['任务','job_id','mono'],['报告','report_url']]);
}
loadAll();
</script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "stock-agent-center",
        "version": "0.2.0",
        "mode": "single-deploy",
        "uzi_api_url": settings.uzi_api_url,
        "stock_pool": settings.stock_pool,
        "daily_external_enabled": settings.enable_daily_sync,
        "dingtalk_enabled": settings.enable_dingtalk_notify,
    }


def _submit_to_uzi(
    *,
    symbol: str,
    depth: str,
    score: float | None,
    signal: str | None,
    source: str,
    notify: bool,
    no_resume: bool,
    db: Session,
) -> dict[str, Any]:
    client = UziClient()
    try:
        uzi_response = client.analyze(symbol=symbol, depth=depth, notify=False, no_resume=no_resume)
    except Exception as exc:
        report = UziReport(
            symbol=symbol,
            depth=depth,
            status="submit_failed",
            source=source,
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
        source=source,
        raw_response=json.dumps(uzi_response, ensure_ascii=False),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    if notify:
        notifier.notify_candidate_submitted(symbol=symbol, score=score, depth=depth, job_id=job_id)

    return {
        "uzi_job_id": job_id,
        "uzi_status": status,
        "report_url": report_url,
        "report_id": report.id,
        "uzi_response": uzi_response,
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
            "candidate_id": candidate.id,
        }

    uzi_result = _submit_to_uzi(
        symbol=symbol,
        depth=depth,
        score=request.score,
        signal=request.signal,
        source=request.source,
        notify=request.notify,
        no_resume=request.no_resume,
        db=db,
    )
    return {
        "ok": True,
        "symbol": symbol,
        "depth": depth,
        "decision": decision.action,
        "reason": decision.reason,
        "candidate_id": candidate.id,
        **uzi_result,
    }


@app.post("/api/scan")
def scan(request: ScanRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    symbols = None
    if request.symbols:
        symbols = [item.strip().upper() for item in request.symbols.replace("，", ",").replace("\n", ",").split(",") if item.strip()]
    scanner = StockScanner()
    scan_results = scanner.scan_many(symbols)
    results: list[dict[str, Any]] = []

    for item in scan_results:
        candidate_payload = item.to_candidate()
        decision = decide(item.score, item.signal)
        depth = request.depth or decision.depth
        candidate = StockCandidate(
            symbol=item.symbol,
            score=item.score,
            signal=item.signal,
            source="stock_scanner",
            decision=decision.action,
            depth=depth,
            raw_payload=json.dumps(candidate_payload, ensure_ascii=False),
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        row = {
            "candidate_id": candidate.id,
            "symbol": item.symbol,
            "score": item.score,
            "signal": item.signal,
            "reason": item.reason,
            "decision": decision.action,
            "depth": depth,
        }
        if request.auto_submit and decision.action == "uzi" and depth:
            try:
                row.update(
                    _submit_to_uzi(
                        symbol=item.symbol,
                        depth=depth,
                        score=item.score,
                        signal=item.signal,
                        source="stock_scanner",
                        notify=request.notify,
                        no_resume=False,
                        db=db,
                    )
                )
            except HTTPException as exc:
                row["submit_error"] = exc.detail
        results.append(row)

    return {"ok": True, "count": len(results), "auto_submit": request.auto_submit, "results": results}


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
