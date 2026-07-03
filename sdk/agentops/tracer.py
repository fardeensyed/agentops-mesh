from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from .context import (
    clear_context,
    get_current_context,
    reset_context,
    set_context,
)
from .span import Span, SpanKind, SpanStatus
from .exporter import SpanExporter


# ─────────────────────────────────────────────────────────────────────────────
# SpanContext
# A small helper that makes "with tracer.start_span(...) as ctx:" work.
# It holds the span AND the tokens needed to restore context when done.
# ─────────────────────────────────────────────────────────────────────────────

class SpanContext:
    """
    Returned by tracer.start_span().
    Used as a context manager so spans close automatically.

    Example:
        with tracer.start_span("llm.call", SpanKind.LLM) as ctx:
            ctx.span.set_attribute("model", "gpt-4o")
            # span closes automatically here, even on exception
    """

    def __init__(self, span: Span, tracer: "Tracer"):
        self.span = span          # the actual span data
        self._tracer = tracer     # reference back to tracer so we can finish

    # called automatically when "with" block starts
    def __enter__(self) -> "SpanContext":
        return self

    # called automatically when "with" block ends
    # exc_type, exc_val, exc_tb are filled if an exception happened
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            # an exception happened inside the with block
            # mark span as error and record the message
            self.span.finish_with_error(exc_val)
        else:
            # everything went fine
            self.span.finish(SpanStatus.OK)

        # tell the tracer this span is done
        # tracer will restore context and queue span for export
        self._tracer._close_span(self.span)

        # returning False means we do NOT suppress the exception
        # it will still propagate up to the caller
        # this is almost always what you want
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Tracer
# The main class users interact with.
# One Tracer per application. Created once via agentops.init().
# ─────────────────────────────────────────────────────────────────────────────

class Tracer:
    """
    Creates and manages spans and traces.

    Usage:
        tracer = Tracer(api_key="your-key", endpoint="http://localhost:8000")

        with tracer.start_trace("my-agent-run"):
            with tracer.start_span("openai.call", SpanKind.LLM) as ctx:
                ctx.span.set_attribute("model", "gpt-4o")
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str = "http://localhost:8000",
        service_name: str = "agentops-sdk",
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.service_name = service_name
        self._exporter = SpanExporter(
             api_key=api_key,
             endpoint=endpoint,
)
        self._exporter.start()

        # stores (span, trace_token, span_token) while span is active
        # so we can restore context when it closes
        self._active_spans: Dict[str, tuple] = {}

        # finished spans waiting to be exported
        # exporter will drain this list in background
        self._finished_spans: List[Span] = []

        # will be set when start_trace() is called
        self._current_trace_id: Optional[str] = None
        self._max_finished_spans = 1000

    # ── Trace management ─────────────────────────────────────────────────────

    @contextmanager
    def start_trace(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Generator[Span, None, None]:
        """
        Starts a new top-level trace and a root span.
        Everything inside this block belongs to the same trace.

        Example:
            with tracer.start_trace("research-agent") as root:
                root.set_attribute("user_id", "user_123")
                # all spans created here share root's trace_id
        """
        # generate a fresh trace ID for this entire agent run
        trace_id = uuid.uuid4().hex
        self._current_trace_id = trace_id

        # create the root span — it has no parent
        root_span = Span(
            name=name,
            span_kind=SpanKind.AGENT,
            trace_id=trace_id,
            parent_span_id=None,
        )

        if attributes:
            for key, value in attributes.items():
                root_span.set_attribute(key, value)

        # set this root span as active in context
        trace_tok, span_tok = set_context(trace_id, root_span.span_id)

        # store tokens so we can restore after
        self._active_spans[root_span.span_id] = (
            root_span, trace_tok, span_tok
        )

        try:
            # hand the root span to the caller
            yield root_span
            # if we get here, no exception — mark success
            root_span.finish(SpanStatus.OK)
        except Exception as e:
            # exception inside the with block — mark as error
            root_span.finish_with_error(e)
            raise  # re-raise so the caller still sees the error
        finally:
            # ALWAYS runs — clean up context and queue span for export
            reset_context(trace_tok, span_tok)
            clear_context()
            self._finished_spans.append(root_span)
            self._exporter.enqueue(root_span)
            self._active_spans.pop(root_span.span_id, None)
            self._current_trace_id = None
             # send to background exporter
            

    def start_span(
        self,
        name: str,
        span_kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SpanContext:
        """
        Creates a child span inside the current trace.
        Must be called inside a start_trace() block.

        The span automatically knows its trace_id and parent_span_id
        by reading the current context.

        Example:
            with tracer.start_span("openai.call", SpanKind.LLM) as ctx:
                ctx.span.set_attribute("model", "gpt-4o")
                ctx.span.set_attribute("input_tokens", 142)
        """
        # read current context — who is my parent?
        current_trace_id, parent_span_id = get_current_context()

        if current_trace_id is None:
            # someone called start_span() outside of start_trace()
            # we handle this gracefully by creating a standalone trace
            current_trace_id = uuid.uuid4().hex

        # create the span — it knows its place in the tree
        span = Span(
            name=name,
            span_kind=span_kind,
            trace_id=current_trace_id,
            parent_span_id=parent_span_id,
        )

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        # set THIS span as the new active span in context
        # any spans created inside this block will be children of this one
        trace_tok, span_tok = set_context(current_trace_id, span.span_id)

        # store everything needed to restore when this span closes
        self._active_spans[span.span_id] = (span, trace_tok, span_tok)

        # return SpanContext which handles __enter__ and __exit__
        return SpanContext(span, self)

    def _close_span(self, span: Span) -> None:
        """
        Called by SpanContext.__exit__ when a span finishes.
        Restores context to parent and queues span for export.
        Internal method — users never call this directly.
        """
        entry = self._active_spans.pop(span.span_id, None)
        if entry is None:
            return

        _, trace_tok, span_tok = entry

        # restore context to what it was before this span started
        # this means the parent span becomes active again
        reset_context(trace_tok, span_tok)

        # add to finished list — exporter will pick this up
        self._finished_spans.append(span)
        self._exporter.enqueue(span)
        if len(self._finished_spans) > self._max_finished_spans:
         self._finished_spans = self._finished_spans[-self._max_finished_spans:]

    # ── Inspection helpers ───────────────────────────────────────────────────

    def get_finished_spans(self) -> List[Span]:
        """Returns all finished spans. Useful for testing."""
        return list(self._finished_spans)

    def clear_finished_spans(self) -> None:
        """Clears the finished spans list. Call after export."""
        self._finished_spans.clear()

    def get_active_span_count(self) -> int:
        """How many spans are currently open."""
        return len(self._active_spans)
    def shutdown(self) -> None:
         """ Flush any remaining spans and stop the background exporter."""
         self._exporter.shutdown()