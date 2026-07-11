from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tracer import Tracer


def patch_crewai(tracer: "Tracer") -> None:
    """
    Wraps CrewAI's Agent.execute_task and Crew.kickoff so every
    agent task and full crew run is automatically traced.
    Call once after agentops.init().
    """
    try:
        from crewai import Agent, Crew
    except ImportError:
        return  # crewai not installed, skip silently

    from ..span import SpanKind

    # ── wrap Crew.kickoff — the top-level "run everything" call ──────────────
    original_kickoff = Crew.kickoff

    def patched_kickoff(self, *args, **kwargs):
        with tracer.start_trace("crewai.crew.kickoff") as root:
            root.set_attribute("agent_count", len(self.agents))
            root.set_attribute("task_count", len(self.tasks))
            try:
                result = original_kickoff(self, *args, **kwargs)
                return result
            except Exception:
                raise  # start_trace already captures this as an error span

    Crew.kickoff = patched_kickoff

    # ── wrap Agent.execute_task — each individual agent's turn ───────────────
    original_execute = Agent.execute_task

    def patched_execute_task(self, task, *args, **kwargs):
        span_ctx = tracer.start_span(f"crewai.agent.{self.role}", SpanKind.AGENT)
        span = span_ctx.__enter__()
        span.set_attribute("role", self.role)
        span.set_attribute("task", str(task.description)[:200])

        try:
            result = original_execute(self, task, *args, **kwargs)
            span_ctx.__exit__(None, None, None)
            return result
        except Exception as e:
            span_ctx.__exit__(type(e), e, e.__traceback__)
            raise

    Agent.execute_task = patched_execute_task