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