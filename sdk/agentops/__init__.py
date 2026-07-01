def __init__(
    self,
    api_key: str,
    endpoint: str = "http://localhost:8000",
    service_name: str = "agentops-sdk",
):
    self.api_key = api_key
    self.endpoint = endpoint
    self.service_name = service_name
    self._active_spans: Dict[str, tuple] = {}
    self._finished_spans: List[Span] = []
    self._current_trace_id: Optional[str] = None

    # create and start the background exporter
    self._exporter = SpanExporter(
        endpoint=endpoint,
        api_key=api_key,
    )
    self._exporter.start()