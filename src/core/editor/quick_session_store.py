"""Autosaved quick-session persistence for the Trim editor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ...utils.platform_utils import ensure_dirs, get_data_dir
from .models import EditorSession


class QuickSessionStore:
    """Persist the last Trim editor session in app data."""

    def __init__(self, session_path: Optional[str] = None):
        ensure_dirs()
        self._path = Path(session_path) if session_path else get_data_dir() / "trim_quick_session.json"

    @property
    def path(self) -> Path:
        return self._path

    def save(
        self,
        session: EditorSession,
        *,
        export_state: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "session": session.to_dict(),
            "export": export_state or {},
            "analysis": analysis or {},
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> Optional[dict[str, Any]]:
        if not self._path.exists():
            return None

        payload = json.loads(self._path.read_text(encoding="utf-8"))
        session = EditorSession()
        session.load_snapshot(payload.get("session", {}))
        return {
            "session": session,
            "export": payload.get("export", {}),
            "analysis": payload.get("analysis", {}),
            "path": str(self._path),
        }

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
