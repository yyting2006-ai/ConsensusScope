from pathlib import Path

import pandas as pd

from src.esl_writing_feedback import route_feedback_dataframe
from src.public_gec_benchmark import (
    ParallelSentence,
    build_feedback_candidates,
    build_gold_feedback,
    evaluate_routing_with_gold,
    load_m2_file,
    load_parallel_csv,
)


def test_public_gec_alignment_builds_gold_feedback():
    records = [
        ParallelSentence(
            dataset="unit",
            sample_id="001",
            source="Many student thinks online classes is convenient.",
            reference="Many students think online classes are convenient.",
        )
    ]

    gold = build_gold_feedback(records)

    assert not gold.empty
    assert set(gold["dataset"]) == {"unit"}
    assert {"target_span", "gold_replacement", "gold_issue_type"}.issubset(gold.columns)


def test_public_gec_candidates_route_errors_to_review():
    records = load_parallel_csv(Path("data/public_gec_sample/sample_parallel.csv"))
    gold = build_gold_feedback(records[:2])
    candidates = build_feedback_candidates(gold, include_distractors=True)
    routing = route_feedback_dataframe(candidates["feedback_items"], candidates["review_evidence"])
    evaluation = evaluate_routing_with_gold(routing, candidates["gold_labels"])
    metrics = evaluation["metrics"]
    overall = metrics[metrics["dataset"] == "ALL"].iloc[0]

    assert int(overall["items"]) == len(candidates["feedback_items"])
    assert float(overall["errors_reviewed"]) >= 0.95
    assert set(evaluation["policy_metrics"]["policy"]) == {
        "Accept low; review med/high",
        "Accept low/med; review high",
        "Review all",
    }


def test_m2_loader_reconstructs_corrected_sentence(tmp_path):
    m2_path = tmp_path / "mini.m2"
    m2_path.write_text(
        "\n".join(
            [
                "S She go to school .",
                "A 1 2|||VERB:SVA|||goes|||REQUIRED|||-NONE-|||0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = load_m2_file(m2_path, dataset="mini")

    assert len(rows) == 1
    assert rows[0].source == "She go to school."
    assert rows[0].reference == "She goes to school."
