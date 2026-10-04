"""Analysis results and the OncoGon Next recommendation for an experiment."""

from ..repositories import Record, ResearchRepository
from .common import not_found, require_experiment


def get_analysis(repo: ResearchRepository, experiment_id: str) -> Record:
    require_experiment(repo, experiment_id)
    analysis = repo.get_analysis(experiment_id)
    if analysis is None:
        raise not_found("Analysis")
    return analysis


def get_next_step(repo: ResearchRepository, experiment_id: str) -> Record:
    """An AI-assisted recommendation only — acting on it needs supervisor approval."""
    require_experiment(repo, experiment_id)
    step = repo.get_next_step(experiment_id)
    if step is None:
        raise not_found("Next step")
    return step
