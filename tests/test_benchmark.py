from app.demo_data import get_demo_story
from app.engine import NarrativeDebtEngine


def test_defect_lab_reports_measured_reliability():
    benchmark = NarrativeDebtEngine().run_benchmark(get_demo_story())

    assert benchmark.recall == 1.0
    assert benchmark.precision == 1.0
    assert benchmark.citation_support_rate == 1.0
    assert benchmark.structured_output_rate == 1.0
