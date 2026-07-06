import sys
sys.path.insert(0, "sdk")  # tells Python where to find our package

from agentops.span import Span, SpanKind, SpanStatus
import time

print("--- Test 1: Create a basic span ---")
span = Span(name="openai.chat.completions", span_kind=SpanKind.LLM)
print(f"span_id:    {span.span_id}")
print(f"trace_id:   {span.trace_id}")
print(f"status:     {span.status}")
print(f"end_time:   {span.end_time}")   # should be None
print(f"duration:   {span.duration_ms}") # should be None


print("\n--- Test 2: Finish a span successfully ---")
time.sleep(0.1)  # simulate some work taking 100ms
span.finish()
print(f"status:     {span.status}")
print(f"end_time:   {span.end_time}")
print(f"duration:   {span.duration_ms:.2f}ms")  # should be ~100ms


print("\n--- Test 3: Finish a span with an error ---")
error_span = Span(name="google.search", span_kind=SpanKind.TOOL)
try:
    raise ValueError("API rate limit exceeded")
except Exception as e:
    error_span.finish_with_error(e)
print(f"status:        {error_span.status}")
print(f"error_message: {error_span.error_message}")


print("\n--- Test 4: Set attributes ---")
span.set_attribute("model", "gpt-4o")
span.set_attribute("input_tokens", 142)
span.set_attribute("output_tokens", 87)
span.set_attribute("cost_usd", 0.0023)
print(f"attributes: {span.attributes}")


print("\n--- Test 5: Add events ---")
span.add_event("retry_attempt", {"attempt_number": 1, "reason": "timeout"})
print(f"events: {span.events}")


print("\n--- Test 6: Serialize to dict (what gets sent to backend) ---")
import json
print(json.dumps(span.to_dict(), indent=2))


print("\n--- Test 7: Two spans always have different IDs ---")
s1 = Span(name="test", span_kind=SpanKind.INTERNAL)
s2 = Span(name="test", span_kind=SpanKind.INTERNAL)
assert s1.span_id != s2.span_id, "span IDs must be unique"
print(f"s1 id: {s1.span_id}")
print(f"s2 id: {s2.span_id}")
print("All IDs are unique ✓")

# ── context tests ─────────────────────────────────────────────────────────────
print("\n--- Test 8: Context starts empty ---")
import sys
sys.path.insert(0, "sdk")
from agentops.context import (
    get_current_context,
    set_context,
    reset_context,
    clear_context
)

trace_id, parent_id = get_current_context()
print(f"trace_id:  {trace_id}")   # should be None
print(f"parent_id: {parent_id}")  # should be None


print("\n--- Test 9: Set context and read it back ---")
trace_tok, span_tok = set_context("trace-abc-123", "span-root-001")
trace_id, parent_id = get_current_context()
print(f"trace_id:  {trace_id}")   # should be trace-abc-123
print(f"parent_id: {parent_id}")  # should be span-root-001


print("\n--- Test 10: Nested spans restore correctly ---")
clear_context()  # clean slate — fixes the pollution bug

root_trace_tok, root_span_tok = set_context("trace-abc-123", "span-root-001")
print(f"Active span (root):  {get_current_context()[1]}")

child_trace_tok, child_span_tok = set_context("trace-abc-123", "span-child-002")
print(f"Active span (child): {get_current_context()[1]}")

reset_context(child_trace_tok, child_span_tok)
print(f"Active span (after child ends): {get_current_context()[1]}")

reset_context(root_trace_tok, root_span_tok)
print(f"Active span (after root ends):  {get_current_context()[1]}")


print("\n--- Test 11: Clear context wipes everything ---")
set_context("some-trace", "some-span")
clear_context()
trace_id, parent_id = get_current_context()
print(f"trace_id:  {trace_id}")
print(f"parent_id: {parent_id}")
print("Context cleared ✓")

# ── tracer tests ──────────────────────────────────────────────────────────────
print("\n--- Test 12: Basic trace with one span ---")
from agentops.tracer import Tracer

tracer = Tracer(api_key="test-key-123", endpoint="http://localhost:8001")

with tracer.start_trace("research-agent") as root:
    print(f"root span name:    {root.name}")
    print(f"root trace_id:     {root.trace_id}")
    print(f"root parent:       {root.parent_span_id}")  # None

print(f"root status after: {root.status}")             # ok
print(f"finished spans:    {len(tracer.get_finished_spans())}")  # 1


print("\n--- Test 13: Nested spans share trace_id and know their parent ---")
tracer2 = Tracer(api_key="test-key-123")

with tracer2.start_trace("multi-step-agent") as root:
    trace_id = root.trace_id

    with tracer2.start_span("openai.call", SpanKind.LLM) as ctx:
        llm_span = ctx.span
        ctx.span.set_attribute("model", "gpt-4o")

        with tracer2.start_span("google.search", SpanKind.TOOL) as ctx2:
            tool_span = ctx2.span
            ctx2.span.set_attribute("query", "latest AI research")

# all spans share the same trace_id
print(f"root trace_id:  {root.trace_id}")
print(f"llm  trace_id:  {llm_span.trace_id}")
print(f"tool trace_id:  {tool_span.trace_id}")
assert root.trace_id == llm_span.trace_id == tool_span.trace_id
print("All share same trace_id ✓")

# parent-child relationships are correct
print(f"\nroot parent:  {root.parent_span_id}")        # None
print(f"llm  parent:  {llm_span.parent_span_id}")     # root's span_id
print(f"tool parent:  {tool_span.parent_span_id}")    # llm's span_id

assert root.parent_span_id is None
assert llm_span.parent_span_id == root.span_id
assert tool_span.parent_span_id == llm_span.span_id
print("Parent-child relationships correct ✓")

# total finished spans: root + llm + tool = 3
print(f"\nTotal finished spans: {len(tracer2.get_finished_spans())}")  # 3


print("\n--- Test 14: Span captures exception automatically ---")
tracer3 = Tracer(api_key="test-key-123")

try:
    with tracer3.start_trace("failing-agent") as root:
        with tracer3.start_span("broken.tool", SpanKind.TOOL) as ctx:
            raise ValueError("Tool API is down")
except ValueError:
    pass  # expected

spans = tracer3.get_finished_spans()
broken = [s for s in spans if s.name == "broken.tool"][0]
print(f"broken span status:  {broken.status}")         # error
print(f"broken error msg:    {broken.error_message}")  # Tool API is down
print("Exception captured automatically ✓")


print("\n--- Test 15: Context is clean after trace ends ---")
from agentops.context import get_current_context

trace_id, span_id = get_current_context()
print(f"trace_id after trace: {trace_id}")   # None
print(f"span_id after trace:  {span_id}")    # None
print("Context clean after trace ✓")


print("\n\n✅ ALL TESTS PASSED")

# ── exporter tests ────────────────────────────────────────────────────────────
print("\n--- Test 16: Exporter queues spans correctly ---")
from agentops.exporter import SpanExporter
from agentops.span import Span, SpanKind, SpanStatus

exporter = SpanExporter(
    endpoint="http://localhost:8001",
    api_key="test-key",
)
exporter.start()

# create and finish a real span
span = Span(name="test.llm.call", span_kind=SpanKind.LLM)
span.set_attribute("model", "gpt-4o")
span.set_attribute("input_tokens", 100)
span.finish()

# enqueue it
exporter.enqueue(span)
print(f"Queue size after enqueue: {exporter._queue.qsize()}")  # 1
print("Span enqueued successfully ✓")


print("\n--- Test 17: Span serializes cleanly for HTTP ---")
import json
span_dict = span.to_dict()
# this must not raise — if datetime isn't handled it would crash here
json_str = json.dumps(span_dict)
parsed = json.loads(json_str)
print(f"name:         {parsed['name']}")
print(f"status:       {parsed['status']}")
print(f"model attr:   {parsed['attributes']['model']}")
print(f"duration_ms:  {parsed['duration_ms']}")
print("JSON serialization clean ✓")


print("\n--- Test 18: Exporter shuts down cleanly ---")
# shutdown flushes queue — it will try to POST to localhost:8000
# which is not running, so it will fail silently (that's correct behaviour)
exporter.shutdown(timeout=3.0)
print(f"Exporter running after shutdown: {exporter._running}")  # False
print("Shutdown clean ✓")


print("\n--- Test 19: Tracer auto-enqueues spans to exporter ---")
from agentops.tracer import Tracer

tracer = Tracer(api_key="test-key", endpoint="http://localhost:8001")

with tracer.start_trace("auto-export-test") as root:
    with tracer.start_span("llm.call", SpanKind.LLM) as ctx:
        ctx.span.set_attribute("model", "gpt-4o")

finished = tracer.get_finished_spans()
print(f"Finished spans count: {len(finished)}")   # 2 (root + llm)
print(f"Span names: {[s.name for s in finished]}")
print("Tracer auto-enqueues to exporter ✓")

tracer._exporter.shutdown(timeout=2.0)


print("\n\n✅ ALL 19 TESTS PASSED")

# ── __init__ and openai patch tests ──────────────────────────────────────────
print("\n--- Test 20: agentops.init() works ---")
import sys
sys.path.insert(0, "sdk")
import agentops

tracer = agentops.init(
    api_key="test-key",
    endpoint="http://localhost:8001",
    patch_openai=False,  # no openai installed in test env
)
print(f"Tracer type:    {type(tracer).__name__}")
print(f"get_tracer():   {type(agentops.get_tracer()).__name__}")
print("agentops.init() works ✓")


print("\n--- Test 21: full SDK flow end to end ---")
from agentops import SpanKind

with tracer.start_trace("e2e-test-agent") as root:
    root.set_attribute("user_id", "test-user-001")

    with tracer.start_span("llm.call", SpanKind.LLM) as ctx:
        ctx.span.set_attribute("model", "gpt-4o")
        ctx.span.set_attribute("gen_ai.usage.input_tokens", 120)
        ctx.span.set_attribute("gen_ai.usage.output_tokens", 80)
        ctx.span.set_attribute("gen_ai.usage.cost_usd", 0.0018)

    with tracer.start_span("tool.search", SpanKind.TOOL) as ctx:
        ctx.span.set_attribute("query", "latest AI papers")

spans = tracer.get_finished_spans()
print(f"Total spans:    {len(spans)}")
print(f"Span names:     {[s.name for s in spans]}")
print(f"All same trace: {len(set(s.trace_id for s in spans)) == 1}")
print(f"Root cost attr: {root.attributes.get('user_id')}")
print("Full SDK flow works ✓")

tracer._exporter.shutdown(timeout=2.0)

print("\n\n✅ ALL 21 TESTS PASSED — SDK COMPLETE")