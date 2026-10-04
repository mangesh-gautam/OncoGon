"""Project-scoped reads: details, files, conversations, instructions, tasks, meeting drafts."""

from ..repositories import Record, ResearchRepository
from .common import not_found, require_person, require_project


def list_projects(repo: ResearchRepository) -> list[Record]:
    return repo.list_projects()


def get_project(repo: ResearchRepository, project_id: str) -> Record:
    return require_project(repo, project_id)


def list_files(repo: ResearchRepository, project_id: str) -> list[Record]:
    require_project(repo, project_id)
    return repo.list_project_files(project_id)


def list_conversations(repo: ResearchRepository, project_id: str) -> list[Record]:
    require_project(repo, project_id)
    return repo.list_conversations(project_id)


def get_current_instruction(repo: ResearchRepository, project_id: str) -> Record:
    """The newest supervisor instruction, with the supervisor's details attached."""
    require_project(repo, project_id)
    instructions = repo.list_instructions(project_id)
    if not instructions:
        raise not_found("Instruction")
    instruction = instructions[-1]
    instruction["supervisor"] = require_person(repo, instruction.pop("from_id"))
    return instruction


def list_tasks(repo: ResearchRepository, project_id: str) -> list[Record]:
    require_project(repo, project_id)
    return repo.list_tasks(project_id)


def get_meeting_draft(repo: ResearchRepository, project_id: str) -> Record:
    """A pre-filled supervisor meeting request. Sending it always needs the user's confirmation."""
    require_project(repo, project_id)
    draft = repo.get_meeting_draft(project_id)
    if draft is None:
        raise not_found("Meeting draft")
    draft["recipient"] = require_person(repo, draft.pop("recipient_id"))
    return draft
