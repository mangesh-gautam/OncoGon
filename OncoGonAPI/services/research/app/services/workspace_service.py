"""The signed-in user's current project, experiment and supervisor."""

from ..deps import CurrentUser
from ..repositories import Record, ResearchRepository
from .common import require_experiment, require_person, require_project


def get_workspace(repo: ResearchRepository, user: CurrentUser) -> Record:
    workspace = repo.get_workspace(user.id)
    project = require_project(repo, workspace["current_project_id"])
    return {
        "meta": repo.get_meta(),
        "supervisor": require_person(repo, project["supervisor_id"]),
        "project": project,
        "experiment": require_experiment(repo, workspace["current_experiment_id"]),
    }
