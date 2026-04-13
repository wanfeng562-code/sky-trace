from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiTestResult:
    name: str
    ok: bool
    status_code: int | None
    message: str
    preview: Any = None
    duration_ms: float | None = None
    category: str | None = None


def format_preview(value: Any) -> str:
    if value is None:
        return ""
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except Exception:
        return str(value)
