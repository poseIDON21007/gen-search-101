"""
Governance / Trace Logger
Observability layer that logs all agent inputs/outputs and timing.
Per architecture: Governance / Trace Logger wraps the entire orchestration.
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class TraceLogger:
    """Governance / Trace Logger: records every agent step for observability.

    Wraps the full pipeline. In production this would push to Cloud Trace / Cloud Logging.
    For hackathon we log to console + in-memory store.
    """

    def __init__(self):
        self.logger = logging.getLogger("GovernanceTrace")
        self._traces: list = []
        self._current_trace: Optional[Dict[str, Any]] = None
        print("✓ Governance / Trace Logger initialized")

    def start_trace(self, query: str, user_id: str = None, session_id: str = None) -> str:
        """Start a new trace for a user request."""
        trace_id = f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self._current_trace = {
            "trace_id": trace_id,
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "status": "in_progress",
        }
        self.logger.info(f"[{trace_id}] TRACE START | query='{query}'")
        return trace_id

    def log_step(self, agent_name: str, input_data: Any, output_data: Any,
                 duration_ms: float, status: str = "success", error: str = None):
        """Log a single agent step."""
        step = {
            "agent": agent_name,
            "started_at": datetime.now().isoformat(),
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "input_summary": self._summarize(input_data),
            "output_summary": self._summarize(output_data),
        }
        if error:
            step["error"] = error

        if self._current_trace:
            self._current_trace["steps"].append(step)

        level = logging.ERROR if status == "error" else logging.INFO
        self.logger.log(
            level,
            f"[{self._current_trace['trace_id'] if self._current_trace else '?'}] "
            f"{agent_name} | {duration_ms:.0f}ms | {status}"
        )

    def end_trace(self, final_response: str = None):
        """End the current trace."""
        if not self._current_trace:
            return

        self._current_trace["ended_at"] = datetime.now().isoformat()
        self._current_trace["status"] = "completed"
        self._current_trace["final_response"] = (final_response or "")[:200]

        total_ms = sum(s["duration_ms"] for s in self._current_trace["steps"])
        self._current_trace["total_duration_ms"] = round(total_ms, 2)

        self.logger.info(
            f"[{self._current_trace['trace_id']}] TRACE END | "
            f"total={total_ms:.0f}ms | steps={len(self._current_trace['steps'])}"
        )

        self._traces.append(self._current_trace)
        self._current_trace = None

    def get_traces(self, limit: int = 10) -> list:
        return self._traces[-limit:]

    def get_last_trace(self) -> Optional[Dict[str, Any]]:
        return self._traces[-1] if self._traces else None

    def _summarize(self, data: Any) -> str:
        """Create a short summary of data for logging."""
        if data is None:
            return "null"
        if isinstance(data, str):
            return data[:100]
        if isinstance(data, dict):
            keys = list(data.keys())[:6]
            return f"dict({len(data)} keys: {keys})"
        if isinstance(data, list):
            return f"list({len(data)} items)"
        return str(data)[:100]


def timed_agent_call(trace_logger: TraceLogger, agent_name: str):
    """Decorator / context-manager helper to time an agent call."""
    class _Timer:
        def __init__(self):
            self.start = None
            self.input_data = None
            self.output_data = None

        def __enter__(self):
            self.start = time.time()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.time() - self.start) * 1000
            if exc_type:
                trace_logger.log_step(
                    agent_name, self.input_data, None,
                    duration_ms, status="error", error=str(exc_val),
                )
            else:
                trace_logger.log_step(
                    agent_name, self.input_data, self.output_data,
                    duration_ms, status="success",
                )
            return False  # Don't suppress exceptions

    return _Timer()
