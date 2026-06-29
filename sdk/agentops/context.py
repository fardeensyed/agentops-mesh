from __future__ import annotations
from contextvars import ContextVar, Token
from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# These are the two "invisible backpacks" that follow your code everywhere.
# When you start a new span, it looks inside these backpacks to know:
#   1. Which trace am I part of?
#   2. Who is my parent span?
# ─────────────────────────────────────────────────────────────────────────────

_current_trace_id: ContextVar[Optional[str]] = ContextVar(
    "_current_trace_id",
    default=None
    # default=None means: if nobody has set this yet,
    # there is no active trace — this span will start a brand new one
)

_current_span_id: ContextVar[Optional[str]] = ContextVar(
    "_current_span_id",
    default=None
    # default=None means: if nobody has set this yet,
    # this span has no parent — it is the root span
)


# ─────────────────────────────────────────────────────────────────────────────
# Reading the context
# These two functions are how the Tracer asks:
# "is there already an active trace/span right now?"
# ─────────────────────────────────────────────────────────────────────────────

def get_current_trace_id() -> Optional[str]:
    """Returns the active trace ID, or None if no trace is running."""
    return _current_trace_id.get()


def get_current_span_id() -> Optional[str]:
    """Returns the active span ID, or None if no span is running."""
    return _current_span_id.get()


def get_current_context() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (trace_id, parent_span_id) for the current execution context.
    
    The Tracer calls this when creating a new span to know:
    - trace_id:      which trace to attach this span to
    - parent_span_id: who is this span's parent (None = root span)
    
    Example:
        trace_id, parent_id = get_current_context()
        # trace_id = "abc123" (join existing trace)
        # parent_id = "span456" (my parent is span456)
    """
    return _current_trace_id.get(), _current_span_id.get()


# ─────────────────────────────────────────────────────────────────────────────
# Writing to the context
# These functions are called by the Tracer when a span STARTS and ENDS.
#
# IMPORTANT: ContextVar.set() returns a Token.
# That Token is like an "undo ticket" — you hand it to reset_context()
# when the span ends, and it restores the previous state.
#
# This is critical for nested spans:
#   Span A starts  → context = (trace1, spanA)
#   Span B starts  → context = (trace1, spanB)   ← spanB is child of A
#   Span B ends    → context = (trace1, spanA)   ← restored! A is active again
#   Span A ends    → context = (None, None)       ← restored! nothing active
# ─────────────────────────────────────────────────────────────────────────────

def set_context(
    trace_id: str,
    span_id: str
) -> Tuple[Token, Token]:
    """
    Sets the active trace and span in context.
    Returns two Tokens needed to undo this later.
    
    Always store the returned tokens and pass them to reset_context()
    when the span finishes. If you don't, nested spans break.
    """
    trace_token = _current_trace_id.set(trace_id)
    span_token  = _current_span_id.set(span_id)
    return trace_token, span_token


def reset_context(
    trace_token: Token,
    span_token: Token
) -> None:
    """
    Restores context to what it was before set_context() was called.
    Call this in the span's finally block so it always runs, even on error.
    
    Example:
        trace_tok, span_tok = set_context(trace_id, span_id)
        try:
            ... do work ...
        finally:
            reset_context(trace_tok, span_tok)  # always runs
    """
    _current_trace_id.reset(trace_token)
    _current_span_id.reset(span_token)


def clear_context() -> None:
    """
    Wipes the context completely.
    Call this at the very end of a top-level trace to clean up.
    Prevents context leaking between separate agent runs.
    """
    _current_trace_id.set(None)
    _current_span_id.set(None)