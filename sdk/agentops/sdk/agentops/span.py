from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class SpanStatus(str, Enum):
    # str + Enum means this serializes to a plain string in JSON
    # e.g. SpanStatus.OK becomes "ok" automatically
    UNSET = "unset"   # span created but not finished yet
    OK    = "ok"      # span finished successfully
    ERROR = "error"   # span finished with an error


class SpanKind(str, Enum):
    # what type of work this span represents
    LLM      = "llm"       # a call to a language model
    TOOL     = "tool"      # a tool/function the agent called
    AGENT    = "agent"     # the top-level agent run itself
    CHAIN    = "chain"     # a sequence of steps (LangChain concept)
    INTERNAL = "internal"  # any other internal work


@dataclass
class Span:
    # ------------------------------------------------------------------ #
    # Required fields — must be provided when creating a span
    # ------------------------------------------------------------------ #
    name: str          # human-readable name e.g. "openai.chat.completions"
    span_kind: SpanKind  # what type of work this is

    # ------------------------------------------------------------------ #
    # Auto-generated fields — you never set these manually
    # ------------------------------------------------------------------ #
    span_id: str = field(
        default_factory=lambda: uuid.uuid4().hex
        # uuid4() = random UUID, .hex strips the dashes
        # default_factory means: call this function each time a Span is made
        # we can't write default=uuid.uuid4().hex because that would generate
        # ONE id at class definition time and every span would share it
    )
    trace_id: str = field(
        default_factory=lambda: uuid.uuid4().hex
        # will be overwritten by the Tracer when a span joins an existing trace
    )
    start_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
        # captured the moment the span is created
    )

    # ------------------------------------------------------------------ #
    # Optional fields — filled in as the span progresses
    # ------------------------------------------------------------------ #
    parent_span_id: Optional[str] = None
    # None means this is a root span (no parent)
    # If set, this span is a child of another span

    end_time: Optional[datetime] = None
    # None until span.finish() is called

    status: SpanStatus = SpanStatus.UNSET
    # starts as UNSET, becomes OK or ERROR when finished

    error_message: Optional[str] = None
    # only populated if status == ERROR

    # ------------------------------------------------------------------ #
    # Attribute bags — flexible key/value storage
    # ------------------------------------------------------------------ #
    attributes: Dict[str, Any] = field(default_factory=dict)
    # anything you want to record: model name, token counts, prompt, etc.
    # e.g. {"model": "gpt-4o", "input_tokens": 142, "output_tokens": 87}

    events: list = field(default_factory=list)
    # timestamped things that happened during the span
    # e.g. [{"name": "retry", "timestamp": "...", "attributes": {...}}]

    # ------------------------------------------------------------------ #
    # Methods
    # ------------------------------------------------------------------ #
    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Call this when the work this span represents is done."""
        self.end_time = datetime.now(timezone.utc)
        self.status = status

    def finish_with_error(self, error: Exception) -> None:
        """Call this when the work failed."""
        self.end_time = datetime.now(timezone.utc)
        self.status = SpanStatus.ERROR
        self.error_message = str(error)

    def set_attribute(self, key: str, value: Any) -> None:
        """Add a single key-value pair to this span's attributes."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """Record a timestamped event that happened during this span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {}
        })

    @property
    def duration_ms(self) -> Optional[float]:
        """How long this span took in milliseconds. None if not finished."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert this span to a plain dict so it can be sent as JSON."""
        return {
            "span_id":        self.span_id,
            "trace_id":       self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name":           self.name,
            "span_kind":      self.span_kind.value,
            "status":         self.status.value,
            "error_message":  self.error_message,
            "start_time":     self.start_time.isoformat(),
            "end_time":       self.end_time.isoformat() if self.end_time else None,
            "duration_ms":    self.duration_ms,
            "attributes":     self.attributes,
            "events":         self.events,
        }