from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError:
    BaseCallbackHandler = object  # allows import even if langchain isn't installed


class AgentOpsCallbackHandler(BaseCallbackHandler):
    """
    Drop-in LangChain callback that auto-traces every chain, LLM call,
    and tool use — zero changes needed to existing LangChain code.

    Usage:
        handler = AgentOpsCallbackHandler(tracer)
        chain.invoke(input, config={"callbacks": [handler]})
    """

    def __init__(self, tracer):
        self.tracer = tracer
        # maps LangChain's run_id -> our SpanContext, so we know
        # which span to close when LangChain tells us a run ended
        self._active: Dict[UUID, Any] = {}

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs):
        from ..span import SpanKind
        span_ctx = self.tracer.start_span("langchain.llm", SpanKind.LLM)
        span_ctx.span.set_attribute("model", serialized.get("id", ["unknown"])[-1])
        span_ctx.span.set_attribute("prompt_count", len(prompts))
        self._active[run_id] = span_ctx

    def on_llm_end(self, response, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            usage = getattr(response, "llm_output", {}) or {}
            token_usage = usage.get("token_usage", {})
            span_ctx.span.set_attribute(
                "input_tokens", token_usage.get("prompt_tokens", 0)
            )
            span_ctx.span.set_attribute(
                "output_tokens", token_usage.get("completion_tokens", 0)
            )
            span_ctx.__exit__(None, None, None)

    def on_llm_error(self, error, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            span_ctx.__exit__(type(error), error, error.__traceback__)

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        from ..span import SpanKind
        span_ctx = self.tracer.start_span("langchain.tool", SpanKind.TOOL)
        span_ctx.span.set_attribute("tool_name", serialized.get("name", "unknown"))
        span_ctx.span.set_attribute("input", str(input_str)[:200])
        self._active[run_id] = span_ctx

    def on_tool_end(self, output, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            span_ctx.__exit__(None, None, None)

    def on_tool_error(self, error, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            span_ctx.__exit__(type(error), error, error.__traceback__)

    def on_chain_start(self, serialized, inputs, *, run_id, **kwargs):
        from ..span import SpanKind
        span_ctx = self.tracer.start_span("langchain.chain", SpanKind.CHAIN)
        self._active[run_id] = span_ctx

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            span_ctx.__exit__(None, None, None)

    def on_chain_error(self, error, *, run_id, **kwargs):
        span_ctx = self._active.pop(run_id, None)
        if span_ctx:
            span_ctx.__exit__(type(error), error, error.__traceback__)