# AgentOps Mesh 🕸️

> The control plane for AI agents in production — observe, evaluate,
> govern, and optimize any agent from any framework.

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-orange)]()

## What is this?

AgentOps Mesh is an open-source observability and governance platform
for AI agents. Think Datadog + Sentry, built specifically for
LLM-powered agents running in production. Framework-agnostic — works
with LangChain, CrewAI, OpenAI Assistants, and custom agents.

## The Problem

AI agents are exploding in adoption but running them reliably in
production is extremely hard:

- No standard way to trace why agents fail across multi-step tool calls
- No cost-per-task analytics — token costs ≠ business ROI
- No governance layer — security teams can't audit what agents do
- Existing tools are framework-locked or incomplete

## How It Works

```python
import agentops

tracer = agentops.init(api_key="your-key")

# Every OpenAI call is automatically traced — zero code changes
with tracer.start_trace("research-agent") as root:
    with tracer.start_span("openai.call", SpanKind.LLM) as ctx:
        ctx.span.set_attribute("model", "gpt-4o")
        # your agent code here — fully instrumented
```

LangChain and CrewAI agents are traced automatically too — zero
changes to existing agent code.

## Live Dashboard

Every trace and span is queryable and clickable in a live Next.js
dashboard — trace list, span waterfall with error propagation, and
cost/ROI analytics aggregated from real span data.

## Governance

Every span passes through PII redaction (emails, phone numbers, SSNs,
credit cards auto-detected and redacted) before storage. Per-project
spend limits are enforced at ingestion time — agents exceeding budget
are blocked with a clear error, not silently allowed to keep spending.

## Core Features

- [x] Universal span and trace data model (OpenTelemetry-compatible)
- [x] Context propagation across nested and async agent calls
- [x] Automatic span lifecycle management with exception capture
- [x] Background HTTP exporter with batching and retry
- [x] OpenAI auto-instrumentation
- [x] LangChain callback integration
- [x] CrewAI integration
- [x] FastAPI ingestion gateway
- [x] ClickHouse trace storage (persistent)
- [x] PostgreSQL metadata + real API key authentication
- [x] Next.js dashboard — trace list, span waterfall, cost analytics
- [x] Governance layer — PII redaction + spend limit enforcement
- [x] docker-compose for one-command local setup
- [ ] Hermes Agent integration
- [ ] Evaluation studio (trace replay, A/B model testing)

## Architecture

```text
Your AI Agent (LangChain / CrewAI / OpenAI / custom)
│
▼
Python SDK (this repo)
├── span.py       — unit of work data model
├── context.py    — propagates trace/span IDs automatically
├── tracer.py     — creates and manages span lifecycle
├── exporter.py   — batches and ships spans over HTTP
└── integrations/ — openai.py, langchain.py, crewai.py
│
▼
Ingestion Gateway (FastAPI)
├── API key auth (hashed, PostgreSQL-backed)
├── Spend limit enforcement
└── PII redaction
│
├──▶ ClickHouse  (traces — billions of rows, fast aggregation)
└──▶ PostgreSQL  (metadata — users, projects, API keys, spend limits)
│
▼
Next.js Dashboard
├── Trace list view          ✅
├── Span waterfall detail    ✅
├── Cost per task analytics  ✅
└── Governance policy controls (view) ⏳
```

## Tech Stack

| Layer | Technology |
|---|---|
| SDK | Python 3.13 + OpenTelemetry-compatible |
| Ingestion | FastAPI |
| Trace Storage | ClickHouse |
| Metadata | PostgreSQL |
| Frontend | Next.js + Tailwind |
| Infra | Docker Compose |

## Project Status

**Month 1 of 6 — Full stack operational, governance-enabled**

| Component | Status |
|---|---|
| SDK core (span/context/tracer/exporter) | ✅ Complete |
| OpenAI / LangChain / CrewAI integrations | ✅ Complete |
| FastAPI gateway + real Postgres auth | ✅ Complete |
| ClickHouse + PostgreSQL | ✅ Complete |
| Next.js dashboard (list/detail/analytics) | ✅ Complete |
| PII redaction + spend limits | ✅ Complete |
| Hermes Agent integration | ⏳ Up next |
| Evaluation studio | ⏳ Planned |

See `TROUBLESHOOTING.md` for real issues hit and fixed during development.

## Getting Started

```bash
git clone https://github.com/fardeensyed/agentops-mesh.git
cd agentops-mesh

python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

docker-compose up -d
python backend/seed.py          # creates a real API key + spend limit
python tests/test_span.py       # verify everything works

uvicorn backend.app.main:app --reload --port 8001
cd frontend && npm run dev      # localhost:3000
```

## Differentiation

- **Framework-agnostic** — one SDK, three frameworks supported already
- **Governance-first** — PII redaction and spend limits enforced at
  ingestion, not bolted on later — built for regulated industries
- **Cost-per-task ROI** — business metrics, not just token counts
- **Hermes Agent first-class support** (planned) — 140K+ star
  community, no existing observability tool

## Roadmap

| Month | Milestone |
|---|---|
| 1 | SDK + gateway + dashboard + governance — **complete** |
| 2 | Hermes integration. HN launch |
| 3 | Evaluation engine. 3 technical blog posts |
| 4 | 500 GitHub stars. 10 design partners |
| 5 | Hosted cloud version. First paying teams |
| 6 | YC application or pre-seed raise not yet done |

## Contributing

Open-source, MIT licensed. Issues and PRs welcome.

---

Built by [@fardeensyed](https://github.com/fardeensyed)