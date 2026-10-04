"""Read-only repository over the mock data file. Temporary — replace with a real data layer."""

import copy
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .base import Record

MOCK_DATA_FILE = Path(__file__).resolve().parent.parent / "mock" / "mock_data.json"


@lru_cache
def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class MockResearchRepository:
    def __init__(self, path: Path = MOCK_DATA_FILE) -> None:
        self._data = _load(path)

    # Copies so callers can't mutate the cached file contents.
    def _all(self, key: str) -> list[Record]:
        return copy.deepcopy(self._data.get(key, []))

    def _where(self, key: str, **match: str) -> list[Record]:
        return [r for r in self._all(key) if all(r.get(k) == v for k, v in match.items())]

    def _first(self, key: str, **match: str) -> Record | None:
        rows = self._where(key, **match)
        return rows[0] if rows else None

    def get_workspace(self, user_id: str) -> Record:
        # The mock has one demo workspace shared by every signed-in user.
        return copy.deepcopy(self._data["workspace"])

    def get_person(self, person_id: str) -> Record | None:
        return self._first("people", id=person_id)

    def list_projects(self) -> list[Record]:
        return self._all("projects")

    def get_project(self, project_id: str) -> Record | None:
        return self._first("projects", id=project_id)

    def list_project_files(self, project_id: str) -> list[Record]:
        return self._where("files", project_id=project_id)

    def list_conversations(self, project_id: str) -> list[Record]:
        return self._where("conversations", project_id=project_id)

    def list_instructions(self, project_id: str) -> list[Record]:
        return self._where("instructions", project_id=project_id)

    def list_memory_items(self, project_id: str) -> list[Record]:
        return self._where("memory_items", project_id=project_id)

    def list_tasks(self, project_id: str) -> list[Record]:
        return self._where("tasks", project_id=project_id)

    def get_meeting_draft(self, project_id: str) -> Record | None:
        return self._first("meeting_drafts", project_id=project_id)

    def list_experiments(self, project_id: str) -> list[Record]:
        return self._where("experiments", project_id=project_id)

    def get_experiment(self, experiment_id: str) -> Record | None:
        return self._first("experiments", id=experiment_id)

    def get_analysis(self, experiment_id: str) -> Record | None:
        return self._first("analyses", experiment_id=experiment_id)

    def get_next_step(self, experiment_id: str) -> Record | None:
        return self._first("next_steps", experiment_id=experiment_id)

    def get_note_draft(self, experiment_id: str) -> Record | None:
        return self._first("note_drafts", experiment_id=experiment_id)

    def list_uploads(self, experiment_id: str) -> list[Record]:
        return self._where("uploads", experiment_id=experiment_id)

    def list_evidence_types(self) -> list[Record]:
        return self._all("evidence_types")

    def list_apps(self) -> list[Record]:
        return self._all("apps")

    def get_voice_commands(self) -> dict[str, str]:
        return dict(self._data.get("voice_commands", {}))

    def get_meta(self) -> Record:
        return copy.deepcopy(self._data.get("meta", {}))
