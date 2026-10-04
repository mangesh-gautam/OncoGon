from fastapi import HTTPException, status

from ..repositories import Record, ResearchRepository


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found.")


def require_project(repo: ResearchRepository, project_id: str) -> Record:
    project = repo.get_project(project_id)
    if project is None:
        raise not_found("Project")
    return project


def require_experiment(repo: ResearchRepository, experiment_id: str) -> Record:
    experiment = repo.get_experiment(experiment_id)
    if experiment is None:
        raise not_found("Experiment")
    return experiment


def require_person(repo: ResearchRepository, person_id: str) -> Record:
    person = repo.get_person(person_id)
    if person is None:
        raise not_found("Person")
    return person
