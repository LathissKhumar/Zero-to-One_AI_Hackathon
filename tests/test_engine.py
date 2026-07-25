from app.demo_data import get_demo_story
from app.engine import NarrativeDebtEngine


def test_earned_ending_repays_more_debt_than_shock_ending():
    story = get_demo_story()

    result = NarrativeDebtEngine().compare(story, "shock-default", "earned-storm")

    assert result.winner_slug == "earned-storm"
    assert result.options["earned-storm"].debt_health > result.options["shock-default"].debt_health
    assert result.options["shock-default"].risks[0].evidence
    assert len(result.court) == 5
