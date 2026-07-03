from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tracer import Tracer

def patch_openai(tracer: "Tracer") -> None:
    """
    Monkey-patches openai so every chat completion
    is automatically traced. Call once after agentops.init().
    """
    try:
        import openai
    except ImportError:
        return  # openai not installed, skip silently

    from ..span import SpanKind

    original = openai.chat.completions.create

    def patched_create(*args, **kwargs):
        # start a span BEFORE the real call
        span_ctx = tracer.start_span(
            "openai.chat.completions",
            SpanKind.LLM,
        )
        span = span_ctx.__enter__()
        span = span_ctx.span

        # record what we're sending
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.request.model",
                           kwargs.get("model", "unknown"))

        try:
            t0 = time.time()
            response = original(*args, **kwargs)
            latency = (time.time() - t0) * 1000

            # record what came back
            usage = getattr(response, "usage", None)
            if usage:
                inp  = getattr(usage, "prompt_tokens", 0)
                out  = getattr(usage, "completion_tokens", 0)
                span.set_attribute("gen_ai.usage.input_tokens",  inp)
                span.set_attribute("gen_ai.usage.output_tokens", out)
                # rough cost estimate for gpt-4o
                cost = (inp * 0.000005) + (out * 0.000015)
                span.set_attribute("gen_ai.usage.cost_usd",
                                   round(cost, 6))

            span.set_attribute("latency_ms", round(latency, 2))
            span_ctx.__exit__(None, None, None)
            return response

        except Exception as e:
            span_ctx.__exit__(type(e), e, e.__traceback__)
            raise

    # replace the real function with our wrapped version
    openai.chat.completions.create = patched_create