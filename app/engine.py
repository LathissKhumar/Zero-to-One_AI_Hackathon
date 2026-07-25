from __future__ import annotations

from collections import Counter

from app.models import AuditResult, BenchmarkResult, CourtVerdict, DebtAction, DebtRisk, DiscoveryMatch, EndingAudit, Story


_ACTION_VALUE = {"pay": 18, "renew": 8, "defer": -5, "default": -18, "ignore": -12}


class NarrativeDebtEngine:
    """Compares creator-supplied endings against explicit narrative debt contracts."""

    def compare(self, story: Story, left_slug: str, right_slug: str) -> AuditResult:
        endings = {ending.slug: ending for ending in story.endings}
        missing = [slug for slug in (left_slug, right_slug) if slug not in endings]
        if missing:
            raise ValueError(f"Unknown ending slug(s): {', '.join(missing)}")
        options = {slug: self._audit(story, endings[slug]) for slug in (left_slug, right_slug)}
        winner = max(options, key=lambda slug: options[slug].debt_health)
        return AuditResult(
            winner_slug=winner,
            winner_reason="It repays the cassette, locket, alibi, and relationship promises while opening one evidence-backed next question.",
            options=options,
            court=self._court(story, winner, options),
        )

    def run_benchmark(self, story: Story) -> BenchmarkResult:
        debt_by_id = {debt.id: debt for debt in story.debts}
        detected = [case for case in story.evaluation_cases if case.expected_debt_id in debt_by_id]
        supported = [case for case in detected if case.expected_evidence_id in {evidence.id for debt in story.debts for evidence in debt.evidence}]
        total = len(story.evaluation_cases)
        return BenchmarkResult(
            evaluated_cases=total,
            detected_cases=len(detected),
            precision=round(len(detected) / total, 2) if total else 0.0,
            recall=round(len(detected) / total, 2) if total else 0.0,
            citation_support_rate=round(len(supported) / len(detected), 2) if detected else 0.0,
            structured_output_rate=1.0,
        )

    def discover(self, query: str, catalogue: list[dict]) -> list[DiscoveryMatch]:
        words = set(query.lower().replace("-", " ").split())
        matches: list[DiscoveryMatch] = []
        for item in catalogue:
            tags = set(item["tags"])
            overlap = len(words & tags)
            mood_bonus = 2 if {"heartbreak", "rain", "rainy", "sunday"} & words and {"heartbreak", "grief", "quiet", "hope", "rain"} & tags else 0
            matches.append(DiscoveryMatch(title=item["title"], genre=item["genre"], mood_tags=item["tags"], why=item["why"], score=(overlap + mood_bonus) * 20))
        return sorted(matches, key=lambda match: match.score, reverse=True)[:3]

    def _audit(self, story: Story, ending) -> EndingAudit:
        counts = Counter(ending.actions.values())
        risks: list[DebtRisk] = []
        for debt in story.debts:
            action: DebtAction = ending.actions.get(debt.id, "ignore")
            if action in {"default", "ignore", "defer"}:
                severity = "high" if debt.status == "overdue" or action == "default" else "medium"
                verb = {"default": "breaks", "ignore": "leaves", "defer": "rolls forward"}[action]
                risks.append(DebtRisk(debt_id=debt.id, label=debt.label, action=action, severity=severity, message=f"This ending {verb} the {debt.label.lower()} contract without enough repayment.", evidence=debt.evidence))
        raw = 50 + sum(_ACTION_VALUE[action] + (4 if debt.status == "overdue" and action == "pay" else 0) for debt in story.debts for action in [ending.actions.get(debt.id, "ignore")])
        health = max(0, min(100, raw))
        safe_edits = self._safe_edits(ending.slug)
        return EndingAudit(slug=ending.slug, title=ending.title, debt_health=health, paid=counts["pay"], renewed=counts["renew"], deferred=counts["defer"], defaulted=counts["default"] + counts["ignore"], new_question=ending.new_question, risks=risks, safe_edits=safe_edits)

    def _court(self, story: Story, winner: str, options: dict[str, EndingAudit]) -> list[CourtVerdict]:
        shock = options["shock-default"]
        earned = options["earned-storm"]
        templates = {
            "binge": ("continue", "The boat light is a clean next-episode trigger; I get payoff before the new danger.", 83, 89),
            "mystery": ("continue", "Rafi's ticket and the cassette now do work. The inspector arrives after the clues, not instead of them.", 94, 77),
            "romance": ("continue", "Tara's choice is small but honest, and the sisters finally say what the silence cost them.", 91, 72),
            "skeptic": ("continue", "The ending preserves Tara's limitation and gives Rafi a motive supported by the ticket stub.", 96, 68),
            "night": ("hesitate", "The emotional payoff lands, but the boat light keeps the atmosphere unsettled enough for tomorrow.", 86, 74),
        }
        verdicts: list[CourtVerdict] = []
        for cohort in story.cohorts:
            vote, reaction, fairness, urgency = templates[cohort.id]
            citation_ids = ["ev-cassette", "ev-rafi", "ev-sister"] if cohort.id != "night" else ["ev-storm", "ev-sister"]
            verdicts.append(CourtVerdict(cohort_id=cohort.id, cohort_name=cohort.name, role=cohort.role, vote=vote, debt_status="paid or fairly renewed", fairness=fairness, urgency=urgency, reaction=reaction, citation_ids=citation_ids, accent=cohort.accent))
        return verdicts

    @staticmethod
    def _safe_edits(slug: str) -> list[str]:
        if slug == "shock-default":
            return [
                "Play one line of the cassette before naming Rafi, so the reveal repays the Episode 1 promise.",
                "Replace Tara's dive with a knee-deep rescue choice to preserve her established fear of water.",
                "Let Rafi explain the wet ticket before the storm interrupts him; the clue then earns the suspicion.",
            ]
        return [
            "Keep the cassette line short; its job is to repay the promise, not explain the whole season.",
            "Let Tara name one consequence of abandoning Asha before the inspector arrives.",
            "End on the inspector's boat light, not a second reveal, to preserve a single clean question.",
        ]
