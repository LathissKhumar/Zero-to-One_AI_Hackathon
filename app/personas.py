"""Structured, independently attributable Writers Room annotations."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.ledger import LedgerResolver
from app.narrative_models import Series


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

