"""Shared workbench stage definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StageDefinition:
    """Metadata describing a single workbench stage."""

    key: str
    label: str
    icon_name: str | None = None
    description: str = ""
