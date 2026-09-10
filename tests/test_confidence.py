from clarify.confidence import Evidence, apply_confidence
from clarify.schema import Card, CardField


def _bill(**kwargs) -> Card:
    base = dict(
        type="bill",
        sender="City Water",
        action="Pay",
        summary="Pay the bill.",
        fields=[
            CardField(key="amount", label="Amount", value="84.12 USD", status="sure"),
            CardField(key="deadline", label="Deadline", value="2026-09-21", status="sure"),
        ],
    )
    base.update(kwargs)
    return Card.model_validate(base)


def test_missing_from_page_is_unsure():
    card = apply_confidence(
        _bill(),
        Evidence(text_layer="City Water amount due 84.12 USD", vision_values=None, source="file"),
    )
    by_key = {f.key: f for f in card.fields}
    assert by_key["amount"].status == "sure"
    assert by_key["deadline"].status == "unsure"
    assert by_key["deadline"].reason == "not on page"


def test_text_vs_vision_disagree_is_unsure():
    card = apply_confidence(
        _bill(),
        Evidence(
            text_layer="amount due 84.12 USD due 2026-09-21",
            vision_values={"amount": "84.00 USD"},
            source="file",
        ),
    )
    assert {f.key: f.status for f in card.fields}["amount"] == "unsure"


def test_visible_fallback_marks_all_unsure():
    card = apply_confidence(
        _bill(),
        Evidence(text_layer="amount due 84.12 USD due 2026-09-21", vision_values=None, source="visible_fallback"),
    )
    assert all(f.status == "unsure" for f in card.fields)
    assert card.fields[0].reason == "visible text fallback"


def test_no_evidence_cannot_check():
    card = apply_confidence(_bill(), Evidence(text_layer=None, vision_values=None, source="file"))
    assert all(f.status == "unsure" and f.reason == "cannot check" for f in card.fields)
