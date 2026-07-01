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
- [ ] OpenAI / LangChain / CrewAI auto-instrumentation
- [ ] FastAPI ingestion gateway
- [ ] ClickHouse trace storage
- [ ] Cost & ROI analytics dashboard
- [ ] Governance layer (PII redaction, spend limits, audit logs)
- [ ] Evaluation studio (trace replay, A/B model testing)

## Architecture