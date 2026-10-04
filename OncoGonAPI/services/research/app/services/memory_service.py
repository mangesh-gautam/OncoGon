"""Research Memory: search across a project's notes, results, instructions and images."""

from ..repositories import Record, ResearchRepository
from .common import require_project


def search(repo: ResearchRepository, project_id: str, category: str | None = None, query: str | None = None) -> list[Record]:
    require_project(repo, project_id)
    q = (query or "").strip().lower()
    return [
        item
        for item in repo.list_memory_items(project_id)
        if (not category or category == "All" or item["category"] == category)
        and (not q or q in f"{item['title']} {item['meta']} {item['tag']}".lower())
    ]
