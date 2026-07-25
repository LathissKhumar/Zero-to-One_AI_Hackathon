from __future__ import annotations

from app.models import CandidateEnding, Cohort, Debt, Episode, EvaluationCase, Evidence, Story


def get_demo_story() -> Story:
    cassette = Evidence(
        id="ev-cassette",
        episode=1,
        label="The cassette promise",
        excerpt="Asha finds her father's cassette labelled: PLAY THIS ONLY WHEN THE RAIN RETURNS.",
    )
    locket = Evidence(
        id="ev-locket",
        episode=2,
        label="The locket clue",
        excerpt="Tara notices a brass locket stamped with the ferry's old route number.",
    )
    swim = Evidence(
        id="ev-swim",
        episode=3,
        label="Tara's limitation",
        excerpt="Tara admits she never learned to swim after the flood took her brother.",
    )
    rafi = Evidence(
        id="ev-rafi",
        episode=4,
        label="Rafi's alibi",
        excerpt="Rafi says he was stranded inland the night of the ferry fire; Asha pockets his wet ticket stub.",
    )
    sister = Evidence(
        id="ev-sister",
        episode=5,
        label="The sisters' wound",
        excerpt="Asha tells Tara: 'You left me with the silence. One day you will tell me why.'",
    )
    storm = Evidence(
        id="ev-storm",
        episode=6,
        label="The monsoon deadline",
        excerpt="The radio warns that the once-in-twelve-years storm reaches the seawall at midnight.",
    )
    debts = [
        Debt(id="cassette", label="The cassette confession", kind="mystery", status="overdue", opened_episode=1, urgency=5, description="Listeners expect the father's warning to reveal who caused the ferry fire.", evidence=[cassette]),
        Debt(id="locket", label="The ferry locket", kind="causal", status="maturing", opened_episode=2, urgency=4, description="The route number must connect to a person or event, not remain set dressing.", evidence=[locket]),
        Debt(id="tara-swim", label="Tara's fear of water", kind="emotional", status="maturing", opened_episode=3, urgency=3, description="Tara needs to confront, not magically erase, the trauma that keeps her from water.", evidence=[swim]),
        Debt(id="rafi-alibi", label="Rafi's wet ticket stub", kind="mystery", status="overdue", opened_episode=4, urgency=5, description="The ticket stub challenges Rafi's alibi and requires a fair payoff.", evidence=[rafi]),
        Debt(id="sisters", label="Asha and Tara's silence", kind="relationship", status="overdue", opened_episode=5, urgency=4, description="The sisters owe each other an explanation before a final rupture can feel earned.", evidence=[sister]),
        Debt(id="seawall", label="The midnight seawall", kind="genre", status="fresh", opened_episode=6, urgency=5, description="The storm must create an immediate, concrete thriller choice.", evidence=[storm]),
    ]
    episodes = [
        Episode(number=1, title="The Tape", summary="Asha receives a cassette from her missing father as the monsoon returns."),
        Episode(number=2, title="Route 17", summary="A brass locket points Asha and detective Tara toward the burned ferry route."),
        Episode(number=3, title="Dry Ground", summary="Tara reveals why she cannot enter deep water."),
        Episode(number=4, title="The Ticket", summary="Rafi's wet ticket stub contradicts his alibi for the ferry fire."),
        Episode(number=5, title="The Silence", summary="Asha forces Tara to acknowledge the years she disappeared after the flood."),
        Episode(number=6, title="Twelve-Year Rain", summary="A rare storm threatens the old seawall at midnight."),
        Episode(number=7, title="The Salt Archive", summary="The sisters discover the cassette contains only half a confession."),
        Episode(number=8, title="Before Midnight", summary="Rafi asks Asha to meet alone at the seawall before the water rises."),
    ]
    endings = [
        CandidateEnding(
            slug="shock-default",
            title="A — The Surprise Villain",
            hook="Maximum shock, but it spends trust the story has not earned.",
            text="At midnight, Asha announces that Rafi murdered her father. Rafi is swept away before he can answer. Tara dives into the floodwater to recover the cassette, and the episode ends on an unknown caller whispering Asha's name.",
            actions={"cassette": "ignore", "locket": "ignore", "tara-swim": "default", "rafi-alibi": "default", "sisters": "defer", "seawall": "pay"},
            new_question="Who was the caller?",
        ),
        CandidateEnding(
            slug="earned-storm",
            title="B — The Earned Storm",
            hook="It repays old promises, then opens one clean new question.",
            text="At the seawall, Asha plays the cassette: her father names the route inspector and asks Tara to forgive herself. Rafi produces the locket and admits he forged his alibi to protect Tara, not because he caused the fire. Tara wades in only to knee depth, choosing to save Asha rather than flee. Asha and Tara agree to expose the inspector—until the inspector's boat light appears through the rain.",
            actions={"cassette": "pay", "locket": "pay", "tara-swim": "renew", "rafi-alibi": "pay", "sisters": "pay", "seawall": "pay"},
            new_question="Why is the inspector arriving before the sisters can reach the police?",
        ),
    ]
    cohorts = [
        Cohort(id="binge", name="Mira", role="Binge Listener", focus="momentum and immediate next-episode compulsion", accent="#ffb55e"),
        Cohort(id="mystery", name="Dev", role="Mystery Purist", focus="fair clues and earned reveals", accent="#7cd7ff"),
        Cohort(id="romance", name="Naina", role="Emotion Listener", focus="relationship payoff and emotional honesty", accent="#ff79c6"),
        Cohort(id="skeptic", name="Ishan", role="Skeptic", focus="motivation, causality, and internal logic", accent="#9bffb5"),
        Cohort(id="night", name="Zoya", role="Late-Night Listener", focus="clarity, atmosphere, and a satisfying aftertaste", accent="#bc9cff"),
    ]
    cases = [
        EvaluationCase(id="case-1", category="debt", expected_debt_id="cassette", expected_evidence_id="ev-cassette"),
        EvaluationCase(id="case-2", category="debt", expected_debt_id="locket", expected_evidence_id="ev-locket"),
        EvaluationCase(id="case-3", category="contradiction", expected_debt_id="tara-swim", expected_evidence_id="ev-swim"),
        EvaluationCase(id="case-4", category="debt", expected_debt_id="rafi-alibi", expected_evidence_id="ev-rafi"),
        EvaluationCase(id="case-5", category="debt", expected_debt_id="sisters", expected_evidence_id="ev-sister"),
        EvaluationCase(id="case-6", category="debt", expected_debt_id="seawall", expected_evidence_id="ev-storm"),
    ]
    return Story(id="last-monsoon", title="The Last Monsoon", genre="Mumbai mystery thriller", premise="A missing father's cassette pulls two estranged sisters into the truth behind a ferry fire.", episodes=episodes, debts=debts, endings=endings, cohorts=cohorts, evaluation_cases=cases)


def get_demo_catalogue() -> list[dict]:
    return [
        {"title": "After the Rain", "genre": "Quiet romance", "tags": ["heartbreak", "grief", "hope", "reconciliation"], "why": "It begins with a wound and pays its emotional debt through a slow, gentle reconciliation."},
        {"title": "Paper Boats", "genre": "Family drama", "tags": ["rain", "nostalgia", "belonging", "healing"], "why": "Its promises are about returning home, making it reflective rather than explosive."},
        {"title": "The Last Monsoon", "genre": "Mystery thriller", "tags": ["rain", "mystery", "guilt", "hope"], "why": "It pairs stormy atmosphere with an emotional promise between estranged sisters."},
        {"title": "The Orange Balcony", "genre": "Romantic comedy", "tags": ["hope", "warmth", "second chance", "humor"], "why": "It uses lightness and a second-chance relationship payoff."},
        {"title": "Salt Letters", "genre": "Literary drama", "tags": ["heartbreak", "grief", "memory", "quiet"], "why": "Its central promise is not revenge but making peace with a lost voice."},
        {"title": "Midnight Platform", "genre": "Suspense", "tags": ["mystery", "tension", "escape", "guilt"], "why": "It is for listeners who want unresolved danger rather than gentle repair."},
    ]
