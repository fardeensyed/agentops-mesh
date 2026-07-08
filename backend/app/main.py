from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .db import init_db, get_db
from .models import User, Project, APIKey
from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import clickhouse_connect
import json

app = FastAPI(title="AgentOps Mesh Gateway")
# allows Next.js dev server (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

# ── ClickHouse connection ────────────────────────────────────────────────────
# created once when the server starts, reused for every request
client = clickhouse_connect.get_client(
    host="localhost",
    port=8123,
    username="default",
    password="agentops123",  # match what you set in Docker
)


class SpanBatch(BaseModel):
    spans: List[Dict[str, Any]]
    service: str



@app.get("/health")
def health():
    return {"status": "okkk"}


@app.post("/v1/spans")
def ingest_spans(
    batch: SpanBatch,
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = authorization.replace("Bearer ", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # ── build rows for ClickHouse insert ─────────────────────────────────────
    # ClickHouse insert() wants a list of lists/tuples matching column order
    rows = []
    for span in batch.spans:
        rows.append([
            span.get("span_id"),
            span.get("trace_id"),
            span.get("parent_span_id"),
            span.get("name"),
            span.get("span_kind"),
            span.get("status"),
            span.get("error_message"),
            span.get("start_time"),
            span.get("end_time"),
            span.get("duration_ms"),
            json.dumps(span.get("attributes", {})),  # dict → JSON string
            json.dumps(span.get("events", [])),       # list → JSON string
        ])

    client.insert(
        "spans",
        rows,
        column_names=[
            "span_id", "trace_id", "parent_span_id", "name",
            "span_kind", "status", "error_message",
            "start_time", "end_time", "duration_ms",
            "attributes", "events",
        ],
    )

    return {"received": len(batch.spans), "status": "ok"}


@app.get("/v1/spans")
def list_spans(limit: int = 50):
    # query ClickHouse directly — real persisted data now
    result = client.query(
        f"SELECT * FROM spans ORDER BY start_time DESC LIMIT {limit}"
    )
    columns = result.column_names
    rows = result.result_rows

    spans = [dict(zip(columns, row)) for row in rows]
    return {"spans": spans, "total": len(spans)}
@app.get("/v1/traces")
def list_traces(limit: int = 50):
    """Groups spans by trace_id — one row per agent run, not per span."""
    result = client.query(f"""
        SELECT
            trace_id,
            argMin(name, start_time) as root_name,
            min(start_time) as started_at,
            max(end_time) as ended_at,
            count() as span_count,
            sumIf(1, status = 'error') as error_count
        FROM spans
        GROUP BY trace_id
        ORDER BY started_at DESC
        LIMIT {limit}
    """)
    columns = result.column_names
    rows = result.result_rows
    traces = [dict(zip(columns, row)) for row in rows]
    return {"traces": traces, "total": len(traces)}