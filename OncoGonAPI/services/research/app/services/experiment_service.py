"""Experiment-scoped reads: details, uploads and voice-note drafts."""

from ..repositories import Record, ResearchRepository
from .common import not_found, require_experiment, require_project


def list_experiments(repo: ResearchRepository, project_id: str) -> list[Record]:
    require_project(repo, project_id)
    return repo.list_experiments(project_id)


def get_experiment(repo: ResearchRepository, experiment_id: str) -> Record:
    return require_experiment(repo, experiment_id)


def get_latest_upload(repo: ResearchRepository, experiment_id: str) -> Record:
    require_experiment(repo, experiment_id)
    uploads = repo.list_uploads(experiment_id)
    if not uploads:
        raise not_found("Upload")
    return uploads[-1]


def get_note_draft(repo: ResearchRepository, experiment_id: str) -> Record:
    require_experiment(repo, experiment_id)
    draft = repo.get_note_draft(experiment_id)
    if draft is None:
        raise not_found("Note draft")
    return draft
