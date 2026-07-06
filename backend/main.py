import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.websockets import WebSocket

APP_DIR = Path(__file__).parent
DB_PATH = os.getenv("COSTFORGE_DB", str(APP_DIR / "costforge.db"))
LOG_PATH = os.getenv("COSTFORGE_LOG", str(APP_DIR / "usage.jsonl"))

app = FastAPI(title="CostForge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROVIDERS_PATH = APP_DIR / "providers.json"
PRICING_PATH = APP_DIR / "pricing.json"

with open(APP_DIR.parent / "pricing" / "catalog.json", "r") as _f:
    PRICE_MAP = json.load(_f)

_providers: list[dict] = []
_pricing: dict[str, dict] = {}


def load_providers() -> list[dict]:
    global _providers
    if not PROVIDERS_PATH.exists():
        return _providers
    with open(PROVIDERS_PATH, "r") as f:
        _providers = json.load(f)
    return _providers


_PROVIDERS_LOCK = asyncio.Lock()


async def get_providers() -> list[dict]:
    async with _PROVIDERS_LOCK:
        if not _providers:
            load_providers()
        return list(_providers)


def load_pricing() -> dict:
    global _pricing
    if not PRICING_PATH.exists():
        return _pricing
    with open(PRICING_PATH, "r") as f:
        _pricing = json.load(f)
    return _pricing


_PRICE_LOCK = asyncio.Lock()


async def get_pricing() -> dict:
    async with _PRICE_LOCK:
        if not _pricing:
            load_pricing()
        return dict(_pricing)


load_pricing()


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    with _db() as c:
        c.execute(
            """create table if not exists usage(
                id integer primary key autoincrement,
                ts text,
                source text,
                model text,
                input_tokens integer default 0,
                output_tokens integer default 0,
                requests integer default 1,
                meta text,
                premium_model text,
                premium_cost_usd real default 0,
                status_code integer default 0,
                estimated integer default 0,
                latency_ms integer default 0
            )""",
        )
        c.execute(
            """create table if not exists events(
                id integer primary key autoincrement,
                ts text,
                kind text,
                detail text
            )""",
        )
        c.execute("create index if not exists idx_usage_ts on usage(ts)")
        c.execute("create index if not exists idx_usage_source on usage(source)")


init_db()


def _record_event(kind: str, detail: str):
    with _db() as c:
        c.execute(
            "insert into events(ts,kind,detail) values(?,?,?)",
            (datetime.utcnow().isoformat(), kind, detail),
        )


# ─── Token / pricing helpers ───────────────────────────────────────────────


def _estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _text_from_request(body: bytes) -> str:
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        return body.decode("utf-8", errors="ignore")

    messages = data.get("messages")
    if isinstance(messages, list):
        return "\n".join(
            m.get("content", "") for m in messages if isinstance(m, dict)
        )
    prompt = data.get("prompt") or data.get("input") or ""
    return prompt if isinstance(prompt, str) else json.dumps(prompt)


def _parse_openai_usage(text: str, body_text: str) -> tuple[int, int, str, bool]:
    try:
        obj = json.loads(text)
    except Exception:
        obj = {}
    usage = obj.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens")
    model = obj.get("model") or "unknown"
    if prompt_tokens is not None or completion_tokens is not None:
        return (
            int(prompt_tokens or 0),
            int(completion_tokens or 0),
            model,
            False,
        )
    # streaming / non-standard response
    prompt_text = _text_from_request(body_text)
    return (
        _estimate_tokens(prompt_text),
        _estimate_tokens(text),
        model or "unknown",
        True,
    )


def _parse_ollama_usage(text: str, body_text: str) -> tuple[int, int, str, bool]:
    try:
        obj = json.loads(text)
    except Exception:
        obj = {}
    prompt_eval = obj.get("prompt_eval_count")
    eval_count = obj.get("eval_count")
    model = obj.get("model") or "unknown"
    if prompt_eval is not None or eval_count is not None:
        return (
            int(prompt_eval or 0),
            int(eval_count or 0),
            model,
            False,
        )
    prompt_text = _text_from_request(body_text)
    return (
        _estimate_tokens(prompt_text),
        _estimate_tokens(text),
        model or "unknown",
        True,
    )


def _parse_generic_usage(text: str, body_text: str) -> tuple[int, int, str, bool]:
    try:
        obj = json.loads(text)
    except Exception:
        obj = {}
    usage = obj.get("usage") or obj.get("meta") or obj.get("metrics") or {}
    prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
    completion_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
    model = obj.get("model") or "unknown"
    if prompt_tokens is not None or completion_tokens is not None:
        return (
            int(prompt_tokens or 0),
            int(completion_tokens or 0),
            model,
            False,
        )
    prompt_text = _text_from_request(body_text)
    return (
        _estimate_tokens(prompt_text),
        _estimate_tokens(text),
        model or "unknown",
        True,
    )


def _premium_equivalent(provider: dict, model: str) -> str:
    mapping = provider.get("premiumEquivalent") or {}
    return mapping.get(model) or mapping.get("default") or "unknown"


def _premium_cost(premium_model: str, tokens_in: int, tokens_out: int) -> float:
    entry = _pricing.get(premium_model)
    if not entry:
        return 0.0
    return (tokens_in / 1_000_000.0) * float(entry.get("inputPerMillion", 0)) + (
        tokens_out / 1_000_000.0
    ) * float(entry.get("outputPerMillion", 0))


# ─── Proxy middleware ───────────────────────────────────────────────────────


@app.api_route("/proxy/{provider_id}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy_handler(request: Request, provider_id: str, path: str):
    providers = await get_providers()
    provider = next((p for p in providers if p.get("id") == provider_id), None)
    if provider is None:
        return Response("Unknown provider", status_code=404)

    base_url = provider.get("baseUrl", "").rstrip("/")
    if not base_url:
        return Response("Invalid provider config", status_code=500)

    url = f"{base_url}/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    body = await request.body()

    method = request.method
    client = request.client.host if request.client else "unknown"

    start = time.time()
    status_code = 500
    response_body = b""
    headers_out: dict[str, str] = {}
    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            resp = await http_client.request(method, url, headers=headers, content=body)
            status_code = resp.status_code
            headers_out = dict(resp.headers)
            response_body = resp.content
    except Exception as exc:
        status_code = 502
        headers_out["content-type"] = "text/plain"
        response_body = f"CostForge proxy error: {exc}".encode()
    elapsed_ms = int((time.time() - start) * 1000)
    try:
        preset = provider.get("responseFormat", "generic")
        if preset == "openai":
            t_in, t_out, model, estimated = _parse_openai_usage(
                response_body.decode("utf-8", errors="ignore"), body,
            )
        elif preset == "ollama":
            t_in, t_out, model, estimated = _parse_ollama_usage(
                response_body.decode("utf-8", errors="ignore"), body,
            )
        else:
            t_in, t_out, model, estimated = _parse_generic_usage(
                response_body.decode("utf-8", errors="ignore"), body,
            )
        premium_model = _premium_equivalent(provider, model)
        premium_cost = _premium_cost(premium_model, t_in, t_out)
    except Exception as exc:
        t_in = t_out = 0
        model = "unknown"
        estimated = True
        premium_model = "unknown"
        premium_cost = 0.0
        _record_event("metering", f"failed: {provider_id}: {exc}")

    with _db() as c:
        c.execute(
            """insert into usage(
                ts,source,model,input_tokens,output_tokens,requests,
                meta,premium_model,premium_cost_usd,status_code,estimated,latency_ms
            ) values(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.utcnow().isoformat(),
                provider.get("label") or provider_id,
                model,
                t_in,
                t_out,
                1,
                json.dumps({"endpoint": url, "client": client, "requestPath": path}),
                premium_model,
                premium_cost,
                status_code,
                1 if estimated else 0,
                elapsed_ms,
            ),
        )
    return Response(
        content=response_body,
        status_code=status_code,
        headers=headers_out,
        media_type=headers_out.get("content-type", "application/octet-stream"),
    )


# ─── Legacy ingest ──────────────────────────────────────────────────────────


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}


@app.post("/ingest")
def ingest(payload: dict):
    source = payload.get("source", "unknown")
    model = payload.get("model", "")
    input_tokens = int(payload.get("input_tokens", 0))
    output_tokens = int(payload.get("output_tokens", 0))
    requests = int(payload.get("requests", 1))
    meta = json.dumps(payload.get("meta", {}))
    premium_model = payload.get("premium_model") or payload.get("meta", {}).get("premium_model", "unknown")
    premium_cost = float(payload.get("premium_cost_usd") or payload.get("meta", {}).get("premium_cost_usd", 0.0))
    ts = payload.get("ts", datetime.utcnow().isoformat())
    with _db() as c:
        c.execute(
            """insert into usage(
                ts,source,model,input_tokens,output_tokens,requests,meta,premium_model,premium_cost_usd
            ) values(?,?,?,?,?,?,?,?,?)""",
            (ts, source, model, input_tokens, output_tokens, requests, meta, premium_model, premium_cost),
        )
    return {"ok": True}


@app.get("/api/usage")
def usage(days: int = 30):
    since = datetime.utcnow() - timedelta(days=days)
    with _db() as c:
        rows = c.execute(
            "select ts,source,model,input_tokens,output_tokens,requests,meta from usage where ts >= ? order by ts asc",
            (since.isoformat(),),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "ts": r["ts"],
                "source": r["source"],
                "model": r["model"],
                "input_tokens": r["input_tokens"],
                "output_tokens": r["output_tokens"],
                "requests": r["requests"],
                "meta": json.loads(r["meta"] or "{}"),
            },
        )
    return JSONResponse(out)


@app.get("/api/summary")
def summary(days: int = 7):
    since = datetime.utcnow() - timedelta(days=days)
    with _db() as c:
        rows = c.execute(
            """select source,model,
                sum(requests) as reqs,
                sum(input_tokens) as in_toks,
                sum(output_tokens) as out_toks,
                sum(premium_cost_usd) as prem
            from usage where ts >= ? group by source,model""",
            (since.isoformat(),),
        ).fetchall()
    total_req = 0
    chart = []
    for r in rows:
        source, model, reqs, inp, outp, prem = r
        total_req += reqs
        chart.append(
            {
                "key": f"{source}::{model or 'free'}",
                "source": source,
                "model": model or "free",
                "requests": reqs,
                "input_tokens": inp or 0,
                "output_tokens": outp or 0,
                "premium_equivalent": prem or 0.0,
                "effective_cost": 0.0,
            },
        )
    return {"days": days, "total_requests": total_req, "items": chart, "pricing_refs": _pricing}


# ─── Dashboard + API routes ─────────────────────────────────────────────────


@app.get("/api/stats")
def api_stats():
    with _db() as c:
        totals = c.execute(
            """select
                count(*) as total_requests,
                coalesce(sum(input_tokens+output_tokens),0) as total_tokens,
                coalesce(sum(premium_cost_usd),0) as premium_cost_usd,
                coalesce(sum(case when estimated=1 then 1 else 0 end),0) as estimated_count
            from usage""",
        ).fetchone()
        by_provider = c.execute(
            """select
                source as provider_id,
                source as provider_label,
                'proxy' as provider_type,
                count(*) as requests,
                coalesce(sum(input_tokens),0) as tokens_in,
                coalesce(sum(output_tokens),0) as tokens_out,
                coalesce(sum(premium_cost_usd),0) as premium_cost_usd
            from usage group by source order by premium_cost_usd desc""",
        ).fetchall()
    return {"totals": dict(totals), "byProvider": [dict(r) for r in by_provider]}


@app.get("/api/recent")
def api_recent(limit: int = 50):
    limit = max(1, min(int(limit), 500))
    with _db() as c:
        rows = c.execute(
            "select * from usage order by ts desc limit ?", (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/timeseries")
def api_timeseries(rangeMinutes: int = 120):
    rangeMinutes = max(1, min(int(rangeMinutes), 10080))
    since = time.time() - rangeMinutes * 60
    with _db() as c:
        rows = c.execute(
            """select (strftime('%s', ts)/60)*60*1000 as bucket,
                coalesce(sum(premium_cost_usd),0) as premium_cost_usd,
                count(*) as requests
            from usage where strftime('%s', ts) >= ? group by bucket order by bucket asc""",
            (int(since),),
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/providers")
async def api_providers():
    providers = await get_providers()
    out = []
    for p in providers:
        out.append(
            {
                "id": p.get("id"),
                "label": p.get("label"),
                "type": p.get("type"),
                "proxyPrefix": p.get("proxyPrefix"),
                "baseUrl": p.get("baseUrl"),
                "notes": p.get("notes"),
            },
        )
    return out


@app.get("/api/pricing")
def api_pricing():
    return _pricing


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (APP_DIR.parent / "frontend" / "dist" / "index.html").read_text()


# ─── WebSocket live feed ────────────────────────────────────────────────────


class LiveHub:
    def __init__(self):
        self._conns: list[WebSocket] = []

    async def register(self, ws: WebSocket):
        self._conns.append(ws)
        try:
            await ws.send_json({"type": "hello", "message": "connected to costforge"})
            await ws.send_json({"type": "usage", "record": await self._fresh_stats()})
        except Exception:
            pass

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    async def _fresh_stats(self) -> dict:
        return {"ts": int(time.time() * 1000)}

    def _broadcast(self, payload: dict):
        for ws in list(self._conns):
            try:
                if ws.client_state == "CONNECTED":
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(ws.send_json(payload))
                    else:
                        asyncio.run(ws.send_json(payload))
            except Exception:
                pass

    def push_usage(self, record: dict):
        self._broadcast({"type": "usage", "record": record})


hub = LiveHub()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await hub.register(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        if ws in hub._conns:
            hub._conns.remove(ws)


@app.get("/api/health")
def api_health():
    return {
        "ok": True,
        "ts": datetime.utcnow().isoformat(),
        "db": DB_PATH,
        "providers": len(_providers),
    }
