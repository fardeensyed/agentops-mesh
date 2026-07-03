from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

app = FastAPI(title="AgentOps Mesh Gateway")

# in-memory store for now — swap for ClickHouse next
_spans_db: List[Dict[str, Any]] = []


class SpanBatch(BaseModel):
    spans: List[Dict[str, Any]]
    service: str


@app.get("/health")
def health():
    return {"status": "ok"}


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

    _spans_db.extend(batch.spans)
    return {"received": len(batch.spans), "status": "ok"}


@app.get("/v1/spans")
def list_spans(limit: int = 50):
    return {"spans": _spans_db[-limit:], "total": len(_spans_db)}