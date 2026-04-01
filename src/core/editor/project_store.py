"""JSON project persistence for Trim editor sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EditorSession


class ProjectStore:
    """Read and write saved Trim editor project files."""

    SCHEMA_VERSION = 1

    def save(
        self,
        path: str,
        session: EditorSession,
        *,
        export_state: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> None:
        project_path = Path(path)
        project_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "session": session.to_dict(),
            "export": export_state or {},
            "analysis": analysis or {},
        }
        project_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: str) -> dict[str, Any]:
        project_path = Path(path)
        payload = json.loads(project_path.read_text(encoding="utf-8"))
        session = EditorSession()
        session.load_snapshot(payload.get("session", {}))
        return {
            "schema_version": int(payload.get("schema_version", 0)),
            "session": session,
            "export": payload.get("export", {}),
            "analysis": payload.get("analysis", {}),
            "path": str(project_path),
        }
