"""Structured, independently attributable Writers Room annotations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from time import monotonic
from typing import Callable

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Series
from app.variant_models import AgentAnnotation


class Persona(BaseModel):
    id: str
    name: str
    focus: str


PERSONAS: tuple[Persona, ...] = (
    Persona(id="continuity", name="Continuity Editor", focus="contradiction and chronology risk"),
    Persona(id="mystery", name="Mystery Architect", focus="clue fairness and reveal timing"),
    Persona(id="emotion", name="Emotional Arc Editor", focus="relationship and emotional obligations"),
    Persona(id="showrunner", name="Serial Showrunner", focus="urgency, momentum, and debt portfolio"),
    Persona(id="localization", name="Localization Editor", focus="culture, language, and translation risk"),
)


class Annotation(BaseModel):
    persona_id: str
    persona_name: str
    target_id: str
    proposed_action: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    citation_ids: list[str] = Field(min_length=1)
    disagreement_group: str
    backend: str = "deterministic-structured"


class IssueDisagreement(BaseModel):
    issue_id: str
    persona_ids: tuple[str, ...]


class WritersRoomResult(BaseModel):
    annotations: list[AgentAnnotation] = Field(default_factory=list)
    timeouts: list[str] = Field(default_factory=list)
    disagreements: list[IssueDisagreement] = Field(default_factory=list)


class AgentRunner:
    """Run one bounded structured annotation without allowing prose output."""

    def __init__(self, handler: Callable | None = None) -> None:
        self.handler = handler or self._default_handler

    def run(self, persona: Persona, graph: Series, budget: int, timeout_s: float) -> AgentAnnotation:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.handler, persona, graph, budget)
        started = monotonic()
        try:
            raw = future.result(timeout=timeout_s)
        except TimeoutError:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            return AgentAnnotation(
                persona_id=persona.id,
                confidence=0.0,
                reason_codes=("timeout",),
                latency_ms=(monotonic() - started) * 1000,
                timed_out=True,
            )
        finally:
            if future.done():
                executor.shutdown(wait=True)
        annotation = AgentAnnotation.model_validate(raw)
        return annotation.model_copy(update={"latency_ms": (monotonic() - started) * 1000})

    @staticmethod
    def _default_handler(persona: Persona, graph: Series, budget: int) -> dict:
        resolved = [item for item in LedgerResolver().resolve_series(graph) if item.state != "paid"]
        issue_ids = (resolved[0].entry.id,) if resolved else ()
        return {
            "persona_id": persona.id,
            "issue_ids": issue_ids,
            "confidence": 0.72,
            "reason_codes": ("structured_ledger_review",),
            "latency_ms": 0.0,
            "timed_out": False,
        }


def run_writers_room(
    graph: Series,
    personas: tuple[Persona, ...] | list[Persona],
    *,
    runner: AgentRunner | None = None,
    budget: int = 512,
    timeout_s: float = 5.0,
) -> WritersRoomResult:
    agent_runner = runner or AgentRunner()
    annotations = [agent_runner.run(persona, graph, budget, timeout_s) for persona in personas]
    timeouts = [annotation.persona_id for annotation in annotations if annotation.timed_out]
    groups: dict[str, list[str]] = {}
    for annotation in annotations:
        for issue_id in annotation.issue_ids:
            groups.setdefault(issue_id, []).append(annotation.persona_id)
    disagreements = [
        IssueDisagreement(issue_id=issue_id, persona_ids=tuple(persona_ids))
        for issue_id, persona_ids in groups.items()
        if len(persona_ids) > 1 or timeouts
    ]
    return WritersRoomResult(annotations=annotations, timeouts=timeouts, disagreements=disagreements)


class WritersRoom:
    def review(self, series: Series, horizon: int | None = None) -> list[Annotation]:
        resolved = [item for item in LedgerResolver().resolve_series(series, as_of=horizon) if item.state != "paid"]
        if not resolved:
            return []
        annotations: list[Annotation] = []
        for index, persona in enumerate(PERSONAS):
            item = resolved[index % len(resolved)]
            citations = [excerpt.id for excerpt in item.citations]
            if not citations:
                continue
            action = "protect and cite the payoff" if item.state == "suspended" else "review before publication"
            annotations.append(Annotation(persona_id=persona.id, persona_name=persona.name, target_id=item.entry.id, proposed_action=action, confidence=0.72, rationale=f"Focus: {persona.focus}. {item.reason}", citation_ids=citations, disagreement_group="ledger-review"))
        return annotations
