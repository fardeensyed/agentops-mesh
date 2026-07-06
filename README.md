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
with LangChain, CrewAI, AutoGen, Hermes Agent, and custom agents.

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

## Core Features

- [x] Universal span and trace data model (OpenTelemetry-compatible)
- [x] Context propagation across nested and async agent calls
- [x] Automatic span lifecycle management with exception capture
- [x] Background HTTP exporter with batching and retry
- [x] OpenAI auto-instrumentation
- [x] FastAPI ingestion gateway
- [x] ClickHouse trace storage (persistent)
- [x] PostgreSQL metadata schema (users, projects, api_keys, agent_configs)
- [ ] Next.js dashboard
- [ ] Governance layer (PII redaction, spend limits, audit logs)
- [ ] Evaluation studio (trace replay, A/B model testing)


## Architecture

```text
Your AI Agent
│
▼
Python SDK (this repo)
├── span.py       — unit of work data model
├── context.py    — propagates trace/span IDs automatically
├── tracer.py     — creates and manages span lifecycle
└── exporter.py   — batches and ships spans over HTTP
│
▼
Ingestion Gateway (FastAPI)
│
├──▶ ClickHouse  (traces — billions of rows, fast aggregation)
└──▶ PostgreSQL  (metadata — users, projects, API keys)
│
▼
Next.js Dashboard
├── Trace waterfall view
├── Cost per task analytics
└── Governance policy controls
```

## Tech Stack

| Layer | Technology |
|---|---|
| SDK | Python 3.13 + OpenTelemetry-compatible |
| Ingestion | FastAPI → Go (high throughput) |
| Trace Storage | ClickHouse |
| Metadata | PostgreSQL |
| Frontend | Next.js + Tailwind + Recharts |
| Deployment | Docker + Kubernetes |

## Project Status

**Month 1 of 6 — Full backend stack operational**

| Component | Status |
|---|---|
| Span data model | ✅ Complete |
| Context propagation | ✅ Complete |
| Tracer (span lifecycle) | ✅ Complete |
| Background exporter | ✅ Complete |
| OpenAI auto-instrumentation | ✅ Complete  |
| FastAPI ingestion gateway | ✅ Complete  |
| ClickHouse + PostgreSQL |✅ Complete |
| Next.js dashboard | ⏳ Up next  |

See `TROUBLESHOOTING.md` for real issues hit and fixed during development.

## Getting Started

```bash
# clone the repo
git clone https://github.com/fardeensyed/agentops-mesh.git
cd agentops-mesh

# create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# install dependencies
pip install httpx tenacity

# run tests
python tests/test_span.py
```

## Differentiation

- **Framework-agnostic** — one SDK for all agent frameworks
- **Hermes Agent first-class support** — 140K+ star community,
  no existing observability tool
- **Governance-first** — PII redaction, spend limits, audit logs
  for regulated industries
- **Cost-per-task ROI** — business metrics, not just token counts

## Roadmap

| Month | Milestone |
|---|---|
| 1 | Python SDK + ingestion gateway + minimal dashboard |
| 2 | LangChain + CrewAI + Hermes integrations. HN launch |
| 3 | Evaluation engine. 3 technical blog posts |
| 4 | Cost analytics + governance policies. 500 GitHub stars |
| 5 | Hosted cloud version. First paying teams |
| 6 | YC application or pre-seed raise |

## Contributing

Open-source, MIT licensed. Issues and PRs welcome.

---

Built by [@fardeensyed](https://github.com/fardeensyed)