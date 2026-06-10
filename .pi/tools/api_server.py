"""FastAPI service and lightweight dashboard for the risk profiler."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Annotated

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent))

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from common.tool_utils import choose_ports, is_target_allowed, logs_dir, parse_target, validate_timeout
from main_pipeline import run_pipeline
from recon.port_scanner import DEFAULT_PORTS


app = FastAPI(
    title="Network Recon + Risk Profiler",
    description="Authorized defensive reconnaissance, risk scoring, and monitoring API.",
    version="2.0.0",
)

audit_logger = logging.getLogger("risk_profiler.api_audit")
scan_lock = threading.Lock()
if not audit_logger.handlers:
    logs_dir().mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(logs_dir() / "api_audit.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False


@app.middleware("http")
async def audit_requests(request: Request, call_next):
    """Record API access without logging request bodies or credentials."""
    response = await call_next(request)
    audit_logger.info(
        "api_request method=%s path=%s status=%s client=%s",
        request.method,
        request.url.path,
        response.status_code,
        request.client.host if request.client else "unknown",
    )
    return response


class ScanRequest(BaseModel):
    target: str = "localhost"
    ports: str = Field(default="", description="Comma list or range, maximum 4096 ports")
    timeout: float = Field(default=0.5, ge=0.01, le=30)
    authorized: bool = False
    offline: bool = True


def _read_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    return json.loads(path.read_text(encoding="utf-8"))


def _api_key_guard(x_api_key: Annotated[str | None, Header()] = None) -> None:
    configured = os.getenv("API_KEY", "").strip()
    if configured and x_api_key != configured:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key.")


def _allow_authorized_override() -> bool:
    return os.getenv("ALLOW_NON_ALLOWLISTED_TARGETS", "").lower() in {"1", "true", "yes"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": app.title, "version": app.version}


@app.get("/api/risk", dependencies=[Depends(_api_key_guard)])
def latest_risk() -> dict:
    path = Path(__file__).resolve().parents[1] / "triage" / "risk_profile.json"
    profile = _read_json(path)
    if not profile:
        raise HTTPException(status_code=404, detail="No risk profile exists. Run a scan first.")
    return profile


@app.get("/api/alerts", dependencies=[Depends(_api_key_guard)])
def latest_alerts() -> dict:
    path = Path(__file__).resolve().parents[1] / "alerts" / "alerts.json"
    return _read_json(path, {"event_count": 0, "alert_count": 0, "alerts": []})


@app.post("/api/scans", dependencies=[Depends(_api_key_guard)])
def create_scan(request: ScanRequest) -> dict:
    try:
        target, url_ports = parse_target(request.target)
        ports = choose_ports(request.ports, url_ports, DEFAULT_PORTS)
        validate_timeout(request.timeout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    authorized = request.authorized and _allow_authorized_override()
    if not is_target_allowed(target, authorized):
        raise HTTPException(
            status_code=403,
            detail="Target is outside the allowlist. Server override is disabled.",
        )
    if not scan_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Another scan is already running.")
    try:
        try:
            return run_pipeline(target, ports, authorized, request.timeout, offline=request.offline)
        except (PermissionError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        scan_lock.release()


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Network Risk Profiler</title>
  <style>
    :root { color-scheme: dark; --bg:#08111f; --panel:#111c2d; --line:#26364c; --text:#eef4ff; --muted:#9fb0c7; --accent:#38bdf8; --danger:#fb7185; }
    * { box-sizing:border-box; }
    body { margin:0; font:16px/1.5 system-ui,sans-serif; background:var(--bg); color:var(--text); }
    main { width:min(1100px,calc(100% - 32px)); margin:0 auto; padding:40px 0 64px; }
    h1,h2 { margin:0; text-wrap:balance; }
    p { color:var(--muted); text-wrap:pretty; }
    .top { display:flex; justify-content:space-between; gap:24px; align-items:end; margin-bottom:28px; }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:20px; }
    .scan { grid-column:span 2; }
    label { display:block; color:var(--muted); margin-bottom:6px; }
    input { width:100%; border:1px solid var(--line); border-radius:8px; background:#0b1524; color:var(--text); padding:10px 12px; }
    button { border:0; border-radius:8px; padding:11px 16px; background:var(--accent); color:#062033; font-weight:700; cursor:pointer; }
    button:focus-visible,input:focus-visible { outline:3px solid white; outline-offset:2px; }
    form { display:grid; grid-template-columns:2fr 2fr 1fr auto; gap:12px; align-items:end; }
    .metric { font-size:2rem; font-variant-numeric:tabular-nums; margin-top:8px; }
    pre { white-space:pre-wrap; overflow-wrap:anywhere; color:#cfe7ff; font-size:.85rem; max-height:360px; overflow:auto; }
    #error { color:var(--danger); min-height:24px; }
    @media (max-width:800px) { .grid,form { grid-template-columns:1fr; } .scan { grid-column:auto; } .top { display:block; } }
  </style>
</head>
<body>
<main>
  <div class="top"><div><h1>Network Risk Profiler</h1><p>Authorized defensive reconnaissance and monitoring.</p></div><strong id="health">Checking service...</strong></div>
  <section class="grid" aria-label="Risk dashboard">
    <article class="panel scan"><h2>Run safe scan</h2><p>Localhost and allowlisted lab targets work by default.</p>
      <form id="scan-form">
        <div><label for="target">Target</label><input id="target" value="localhost" required></div>
        <div><label for="ports">Ports</label><input id="ports" value="8000,8080,3306,5432,6379" required></div>
        <div><label for="timeout">Timeout</label><input id="timeout" type="number" min=".01" max="30" step=".01" value=".5" required></div>
        <button type="submit">Run scan</button>
      </form><div style="margin-top:12px"><label for="api-key">API key (optional)</label><input id="api-key" type="password" autocomplete="off"></div><p id="error" role="alert"></p>
    </article>
    <article class="panel"><h2>Risk score</h2><div class="metric" id="risk-score">--</div><p id="risk-level">No scan yet</p></article>
    <article class="panel"><h2>Open ports</h2><div class="metric" id="open-ports">--</div><p>Latest completed assessment</p></article>
    <article class="panel"><h2>Alerts</h2><div class="metric" id="alert-count">--</div><p>Latest monitoring output</p></article>
    <article class="panel"><h2>Risk drivers</h2><pre id="drivers">No risk profile yet.</pre></article>
    <article class="panel scan"><h2>Latest result</h2><pre id="result">Run a scan to see pipeline metadata.</pre></article>
  </section>
</main>
<script>
const byId=(id)=>document.getElementById(id);
async function json(url,options={}){const key=byId("api-key")?.value||"";options.headers={...(options.headers||{}),...(key?{"X-API-Key":key}:{})};const response=await fetch(url,options);const data=await response.json();if(!response.ok)throw new Error(data.detail||"Request failed");return data;}
async function refresh(){
  try{const h=await json("/health");byId("health").textContent=h.status==="ok"?"Service online":"Service unavailable";}catch(e){byId("health").textContent="Service unavailable";}
  try{const r=await json("/api/risk");byId("risk-score").textContent=r.score+"/10";byId("risk-level").textContent=r.risk_level;byId("open-ports").textContent=r.recon_summary.open_ports.length;byId("drivers").textContent=JSON.stringify(r.ml_model.risk_drivers||[],null,2);}catch(e){}
  try{const a=await json("/api/alerts");byId("alert-count").textContent=a.alert_count;}catch(e){}
}
byId("scan-form").addEventListener("submit",async(event)=>{event.preventDefault();byId("error").textContent="";const button=event.submitter;button.disabled=true;button.textContent="Scanning...";
  try{const result=await json("/api/scans",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({target:byId("target").value,ports:byId("ports").value,timeout:Number(byId("timeout").value),offline:true})});byId("result").textContent=JSON.stringify(result,null,2);await refresh();}
  catch(e){byId("error").textContent=e.message;}finally{button.disabled=false;button.textContent="Run scan";}
});
refresh();
</script>
</body>
</html>"""
