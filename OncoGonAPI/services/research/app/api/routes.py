"""Thin HTTP layer. Every endpoint needs a valid access token; logic lives in `app/services`."""

from fastapi import APIRouter, Depends, Query

from ..deps import CurrentUser, get_repository, require_user
from ..repositories import ResearchRepository
from ..schemas import (
    Analysis,
    AppEntry,
    Conversation,
    EvidenceType,
    Experiment,
    Instruction,
    MeetingDraft,
    MemoryItem,
    NextStep,
    NoteDraft,
    Project,
    ProjectFile,
    Task,
    Upload,
    Workspace,
)
from ..services import (
    analysis_service,
    catalog_service,
    experiment_service,
    memory_service,
    project_service,
    workspace_service,
)

router = APIRouter(prefix="/research", tags=["research"], dependencies=[Depends(require_user)])
Repo = Depends(get_repository)


@router.get("/workspace", response_model=Workspace)
def workspace(user: CurrentUser = Depends(require_user), repo: ResearchRepository = Repo):
    return workspace_service.get_workspace(repo, user)


# Projects


@router.get("/projects", response_model=list[Project])
def list_projects(repo: ResearchRepository = Repo):
    return project_service.list_projects(repo)


@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str, repo: ResearchRepository = Repo):
    return project_service.get_project(repo, project_id)


@router.get("/projects/{project_id}/experiments", response_model=list[Experiment])
def list_experiments(project_id: str, repo: ResearchRepository = Repo):
    return experiment_service.list_experiments(repo, project_id)


@router.get("/projects/{project_id}/files", response_model=list[ProjectFile])
def list_files(project_id: str, repo: ResearchRepository = Repo):
    return project_service.list_files(repo, project_id)


@router.get("/projects/{project_id}/conversations", response_model=list[Conversation])
def list_conversations(project_id: str, repo: ResearchRepository = Repo):
    return project_service.list_conversations(repo, project_id)


@router.get("/projects/{project_id}/instruction", response_model=Instruction)
def current_instruction(project_id: str, repo: ResearchRepository = Repo):
    return project_service.get_current_instruction(repo, project_id)


@router.get("/projects/{project_id}/memory", response_model=list[MemoryItem])
def search_memory(
    project_id: str,
    category: str | None = Query(None, description="Results, Notes, Instructions, Images, AI Summaries, Reference"),
    q: str | None = Query(None, max_length=200),
    repo: ResearchRepository = Repo,
):
    return memory_service.search(repo, project_id, category, q)


@router.get("/projects/{project_id}/tasks", response_model=list[Task])
def list_tasks(project_id: str, repo: ResearchRepository = Repo):
    return project_service.list_tasks(repo, project_id)


@router.get("/projects/{project_id}/meeting-draft", response_model=MeetingDraft)
def meeting_draft(project_id: str, repo: ResearchRepository = Repo):
    return project_service.get_meeting_draft(repo, project_id)


# Experiments


@router.get("/experiments/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: str, repo: ResearchRepository = Repo):
    return experiment_service.get_experiment(repo, experiment_id)


@router.get("/experiments/{experiment_id}/analysis", response_model=Analysis)
def get_analysis(experiment_id: str, repo: ResearchRepository = Repo):
    return analysis_service.get_analysis(repo, experiment_id)


@router.get("/experiments/{experiment_id}/next-step", response_model=NextStep)
def get_next_step(experiment_id: str, repo: ResearchRepository = Repo):
    return analysis_service.get_next_step(repo, experiment_id)


@router.get("/experiments/{experiment_id}/note-draft", response_model=NoteDraft)
def get_note_draft(experiment_id: str, repo: ResearchRepository = Repo):
    return experiment_service.get_note_draft(repo, experiment_id)


@router.get("/experiments/{experiment_id}/uploads/latest", response_model=Upload)
def latest_upload(experiment_id: str, repo: ResearchRepository = Repo):
    return experiment_service.get_latest_upload(repo, experiment_id)


# Catalog


@router.get("/catalog/evidence-types", response_model=list[EvidenceType])
def evidence_types(repo: ResearchRepository = Repo):
    return catalog_service.list_evidence_types(repo)


@router.get("/catalog/apps", response_model=list[AppEntry])
def apps(repo: ResearchRepository = Repo):
    return catalog_service.list_apps(repo)


@router.get("/catalog/voice-commands", response_model=dict[str, str])
def voice_commands(repo: ResearchRepository = Repo):
    return catalog_service.get_voice_commands(repo)
