from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


DebtKind = Literal["mystery", "causal", "relationship", "emotional", "genre"]
DebtStatus = Literal["fresh", "maturing", "overdue", "paid"]
DebtAction = Literal["pay", "renew", "defer", "default", "ignore"]
Vote = Literal["continue", "hesitate", "stop"]


class Evidence(BaseModel):
    id: str
    episode: int
    label: str
    excerpt: str


class Episode(BaseModel):
    number: int
    title: str
    summary: str


class Debt(BaseModel):
    id: str
    label: str
    kind: DebtKind
    status: DebtStatus
    opened_episode: int
    urgency: int = Field(ge=1, le=5)
    description: str
    evidence: list[Evidence]


class CandidateEnding(BaseModel):
    slug: str
    title: str
    hook: str
    text: str
    actions: dict[str, DebtAction]
    new_question: str


class Cohort(BaseModel):
    id: str
    name: str
    role: str
    focus: str
    accent: str


class EvaluationCase(BaseModel):
    id: str
    category: Literal["contradiction", "debt"]
    expected_debt_id: str
    expected_evidence_id: str
    probe_action: DebtAction
    expected_flag: bool


class Story(BaseModel):
    id: str
    title: str
    genre: str
    premise: str
    episodes: list[Episode]
    debts: list[Debt]
    endings: list[CandidateEnding]
    cohorts: list[Cohort]
    evaluation_cases: list[EvaluationCase]


class DebtRisk(BaseModel):
    debt_id: str
    label: str
    action: DebtAction
    severity: Literal["low", "medium", "high"]
    message: str
    evidence: list[Evidence]


class EndingAudit(BaseModel):
    slug: str
    title: str
    debt_health: int = Field(ge=0, le=100)
    paid: int
    renewed: int
    deferred: int
    defaulted: int
    new_question: str
    risks: list[DebtRisk]
    safe_edits: list[str]


class CourtVerdict(BaseModel):
    cohort_id: str
    cohort_name: str
    role: str
    vote: Vote
    debt_status: str
    fairness: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    reaction: str
    citation_ids: list[str]
    accent: str


class AuditResult(BaseModel):
    winner_slug: str
    winner_reason: str
    options: dict[str, EndingAudit]
    court: list[CourtVerdict]


class BenchmarkResult(BaseModel):
    evaluated_cases: int
    detected_cases: int
    precision: float
    recall: float
    citation_support_rate: float
    structured_output_rate: float


class DiscoveryMatch(BaseModel):
    title: str
    genre: str
    mood_tags: list[str]
    why: str
    score: int
