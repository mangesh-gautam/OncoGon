"""Static catalogs: evidence types, OncoGon apps and the scripted demo voice commands."""

from ..repositories import Record, ResearchRepository


def list_evidence_types(repo: ResearchRepository) -> list[Record]:
    return repo.list_evidence_types()


def list_apps(repo: ResearchRepository) -> list[Record]:
    return repo.list_apps()


def get_voice_commands(repo: ResearchRepository) -> dict[str, str]:
    return repo.get_voice_commands()
