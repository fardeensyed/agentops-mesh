from .tracer import Tracer
from .span import Span, SpanKind, SpanStatus
from .exporter import SpanExporter

_global_tracer: Tracer = None

def init(
    api_key: str,
    endpoint: str = "http://localhost:8000",
    service_name: str = "agentops-sdk",
) -> Tracer:
    global _global_tracer
    _global_tracer = Tracer(
        api_key=api_key,
        endpoint=endpoint,
        service_name=service_name,
    )
    return _global_tracer

def get_tracer() -> Tracer:
    if _global_tracer is None:
        raise RuntimeError("Call agentops.init() first")
    return _global_tracer

__all__ = [
    "init",
    "get_tracer",
    "Tracer",
    "Span",
    "SpanKind",
    "SpanStatus",
    "SpanExporter",
]