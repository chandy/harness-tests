from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """Comparable run metrics emitted by every harness CLI."""

    harness: str
    task_id: str
    passed: bool
    steps: int
    wall_time_ms: float
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    model: str = "fake"
    message: str = ""
    error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
