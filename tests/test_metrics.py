# tests/test_metrics.py
import json
from pathlib import Path

from clarify.metrics import score_all
from clarify.schema import Card, CardField

_EVAL = Path(__file__).resolve().parents[1] / "eval"


def test_sure_accuracy_and_catch_rate():
    labeled = Card(
        type="bill",
        action="Pay",
        summary="x",
        fields=[
            CardField(key="amount", label="Amount", value="10 USD"),
            CardField(key="deadline", label="Deadline", value="2026-01-01"),
        ],
    )
    predicted = Card(
        type="bill",
        action="Pay",
        summary="x",
        fields=[
            CardField(key="amount", label="Amount", value="10 USD", status="sure"),
            CardField(key="deadline", label="Deadline", value="2026-02-02", status="unsure"),
        ],
    )
    s = score_all([(predicted, labeled)])
    assert s.sure_accuracy == 1.0
    assert s.catch_rate == 1.0
    assert s.n_wrong_fields == 1


def test_frozen_predictions_meet_baseline():
    labels = json.loads((_EVAL / "labels.json").read_text(encoding="utf-8"))
    preds = json.loads((_EVAL / "predictions.json").read_text(encoding="utf-8"))
    baseline = json.loads((_EVAL / "baseline.json").read_text(encoding="utf-8"))
    assert len(labels) == 40
    assert len(preds) == 40
    by_id = {p["id"]: p for p in preds}
    pairs = [
        (Card.model_validate(by_id[lab["id"]]["card"]), Card.model_validate(lab["card"]))
        for lab in labels
    ]
    s = score_all(pairs)
    assert s.sure_accuracy >= baseline["sure_accuracy"]
    assert s.catch_rate >= baseline["catch_rate"]
    assert s.n_items == 40


def test_eval_set_mix():
    labels = json.loads((_EVAL / "labels.json").read_text(encoding="utf-8"))
    types = [lab["type"] for lab in labels]
    assert len(labels) == 40
    assert types.count("receipt") == 2
    assert types.count("error_screenshot") == 2
    assert types.count("draft_doc") == 1
    assert types.count("spreadsheet") == 1
    assert sum(1 for t in types if t in ("bill", "school_notice")) == 34
    assert (_EVAL / "items" / "doc_snippet.txt").is_file()
    assert (_EVAL / "items" / "sheet.csv").is_file()
    assert (_EVAL / "items" / "error_01.txt").is_file()
    assert (_EVAL / "items" / "error_02.txt").is_file()
