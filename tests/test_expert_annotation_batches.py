from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "expert_annotation_app" / "sample_data"


def test_expert_annotation_batches_are_aligned() -> None:
    feedback = pd.read_csv(SAMPLE_DIR / "feedback_items.csv")
    routing = pd.read_csv(SAMPLE_DIR / "routing_results.csv")

    assert len(feedback) == 30
    assert feedback["feedback_item_id"].is_unique
    assert routing["feedback_item_id"].is_unique
    assert set(feedback["feedback_item_id"]) == set(routing["feedback_item_id"])

    batch_counts = feedback.groupby(feedback["annotation_batch"].astype(str)).size().to_dict()
    assert batch_counts == {"1": 12, "2": 18}


def test_expanded_batch_contains_mixed_routing_actions() -> None:
    routing = pd.read_csv(SAMPLE_DIR / "routing_results.csv")
    batch_two = routing[routing["annotation_batch"].astype(str).eq("2")]

    actions = set(batch_two["recommended_action"])
    assert "auto_accept" in actions
    assert "teacher_review" in actions
    assert len(batch_two) == 18
