"""Response models — the API contract the app depends on, whatever the data source."""

from typing import Literal

from pydantic import BaseModel

DataMode = Literal["SIMULATED", "RESEARCH"]


class DataMeta(BaseModel):
    data_mode: DataMode
    training_eligible: bool
    clinical_use: bool
    note: str | None = None


class Person(BaseModel):
    id: str
    name: str
    role: str
    department: str | None = None


class Project(BaseModel):
    id: str
    title: str
    indication: str
    compound: str
    stage: str
    status: str
    start_date: str
    supervisor_id: str
    current_experiment_id: str | None
    data_mode: DataMode


class Experiment(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    summary: str
    cell_line: str
    conditions: str
    conditions_short: str
    replicates: str
    status: str
    data_mode: DataMode


class Workspace(BaseModel):
    """What the signed-in user is working on right now."""

    meta: DataMeta
    supervisor: Person
    project: Project
    experiment: Experiment


class DetailRow(BaseModel):
    icon: str
    label: str
    value: str


class Instruction(BaseModel):
    id: str
    project_id: str
    experiment_id: str | None
    supervisor: Person
    received_day: str
    received_time: str
    text: str
    details: list[DetailRow]
    notes: str | None


class Conversation(BaseModel):
    id: str
    icon: str
    time: str
    text: str
    kind: Literal["Note", "Analysis", "Evidence"]


class ProjectFile(BaseModel):
    id: str
    kind: str
    title: str
    meta: str


class MemoryItem(BaseModel):
    id: str
    icon: str
    title: str
    date: str
    meta: str
    tag: str
    tag_tone: Literal["blue", "pink"]
    category: str


class Task(BaseModel):
    id: str
    title: str
    meta: str
    done: bool


class MeetingDraft(BaseModel):
    project_id: str
    recipient: Person
    purpose: str
    duration: str
    suggested_time: str
    time_note: str
    attachments: str
    attachments_meta: str


class Upload(BaseModel):
    id: str
    file_name: str
    uploaded: str
    type: str
    size: str
    dimensions: str
    format: str


class NoteDraft(BaseModel):
    experiment_id: str
    transcript: str
    tags: list[str]


class SummaryStat(BaseModel):
    value: str
    label: str
    check: bool


class DosePoint(BaseModel):
    x: float
    y: float
    err: float


class AiAnalysis(BaseModel):
    lead: str
    highlight: str
    tail: str


class Finding(BaseModel):
    title: str
    text: str


class SourceRef(BaseModel):
    id: str
    icon: str
    title: str
    meta: str
    meta2: str | None = None


class Analysis(BaseModel):
    experiment_id: str
    summary: list[SummaryStat]
    dose_response: list[DosePoint]
    ai_analysis: AiAnalysis
    findings: list[Finding]
    sources: list[SourceRef]


class NextStep(BaseModel):
    experiment_id: str
    title: str
    priority: str
    rationale: str
    confidence: int
    confidence_label: str
    requires_supervisor_approval: bool
    evidence_used: list[SourceRef]


class EvidenceType(BaseModel):
    id: str
    icon: str
    title: str
    description: str


class AppEntry(BaseModel):
    id: str
    icon: str
    title: str
    meta: str
