from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SyncJobLog:
    platform: str
    status: str = "csv_export_only"
    messages: list[str] = field(default_factory=list)
