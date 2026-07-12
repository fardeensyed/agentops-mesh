from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .db import init_db, get_db, SessionLocal
from .models import User, Project, APIKey
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from .auth import verify_api_key, hash_key
from .governance import redact_attributes, check_spend_limit
import clickhouse_connect
import json

app = FastAPI(title="AgentOps Mesh Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host="localhost",
        port=8123,
        username="default",
        password="agentops123",
    )


class SpanBatch(BaseModel):
    spans: List[Dict[str, Any]]
    service: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/spans")
def ingest_spans(batch: SpanBatch, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")

    api_key = authorization.replace("Bearer ", "")
    db = SessionLocal()
    try:
        if not verify_api_key(db, api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

        key_record = db.query(APIKey).filter(
            APIKey.key_hash == hash_key(api_key)
        ).first()

        client = get_clickhouse_client()

        spend_status = check_spend_limit(db, key_record.project_id, client)
        if spend_status["blocked"]:
            raise HTTPException(
                status_code=402,
                detail=f"Spend limit exceeded: ${spend_status['spent']} / ${spend_status['limit']}"
            )
    finally:
        db.close()

    rows = []
    for span in batch.spans:
        clean_attributes = redact_attributes(span.get("attributes", {}))
        rows.append([
            span.get("span_id"), span.get("trace_id"), span.get("parent_span_id"),
            span.get("name"), span.get("span_kind"), span.get("status"),
            span.get("error_message"), span.get("start_time"), span.get("end_time"),
            span.get("duration_ms"),
            json.dumps(clean_attributes),
            json.dumps(span.get("events", [])),
        ])

    client.insert(
        "spans", rows,
        column_names=["span_id", "trace_id", "parent_span_id", "name",
                      "span_kind", "status", "error_message",
                      "start_time", "end_time", "duration_ms",
                      "attributes", "events"],
    )
    return {"received": len(batch.spans), "status": "ok"}


@app.get("/v1/spans")
def list_spans(limit: int = 50):
    client = get_clickhouse_client()
    result = client.query(f"SELECT * FROM spans ORDER BY start_time DESC LIMIT {limit}")
    columns = result.column_names
    rows = result.result_rows
    return {"spans": [dict(zip(columns, row)) for row in rows], "total": len(rows)}


@app.get("/v1/traces")
def list_traces(limit: int = 50):
    client = get_clickhouse_client()
    result = client.query(f"""
        SELECT trace_id, argMin(name, start_time) as root_name,
               min(start_time) as started_at, max(end_time) as ended_at,
               count() as span_count, sumIf(1, status = 'error') as error_count
        FROM spans GROUP BY trace_id ORDER BY started_at DESC LIMIT {limit}
    """)
    columns = result.column_names
    rows = result.result_rows
    return {"traces": [dict(zip(columns, row)) for row in rows], "total": len(rows)}


@app.get("/v1/traces/{trace_id}")
def get_trace_detail(trace_id: str):
    client = get_clickhouse_client()
    result = client.query(f"""
        SELECT * FROM spans
        WHERE trace_id = '{trace_id}'
        ORDER BY start_time ASC
    """)
    columns = result.column_names
    rows = result.result_rows
    spans = [dict(zip(columns, row)) for row in rows]
    return {"trace_id": trace_id, "spans": spans}


@app.get("/v1/analytics/cost")
def cost_analytics():
    client = get_clickhouse_client()
    result = client.query("""
        SELECT
            toDate(start_time) as day,
            count() as total_spans,
            sumIf(1, status = 'error') as total_errors,
            sum(JSONExtractFloat(attributes, 'cost_usd')) as total_cost_usd
        FROM spans
        WHERE span_kind = 'llm'
        GROUP BY day
        ORDER BY day ASC
    """)
    daily = [dict(zip(result.column_names, row)) for row in result.result_rows]

    totals = client.query("""
        SELECT
            count() as total_llm_calls,
            sum(JSONExtractFloat(attributes, 'cost_usd')) as total_cost_usd,
            sumIf(1, status = 'error') as total_errors,
            count(DISTINCT trace_id) as total_agent_runs
        FROM spans
        WHERE span_kind = 'llm'
    """)
    totals_row = dict(zip(totals.column_names, totals.result_rows[0]))

    return {"daily": daily, "totals": totals_row}