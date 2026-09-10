import pytest
from clarify.explain import ExplainError, explain
from clarify.extract import Extracted
from clarify.model import FakeExplainModel
from clarify.schema import Card, CardField


def test_oversize_raises():
    with pytest.raises(ExplainError) as ei:
        explain(
            Extracted(kind="image", text_layer=None, image_bytes=None, page_limit_hit=False, source="file", error="oversize"),
            FakeExplainModel(Card(type="other", action="ignore", summary="x")),
        )
    assert ei.value.code == "oversize"


def test_timeout_raises_no_card():
    draft = Card(type="bill", action="Pay", summary="invented")
    with pytest.raises(ExplainError) as ei:
        explain(
            Extracted(kind="text", text_layer="hi", image_bytes=None, page_limit_hit=False, source="selection", error=None),
            FakeExplainModel(draft, fail="timeout"),
        )
    assert ei.value.code == "timeout"


def test_page_limit_copied_and_confidence_applied():
    draft = Card(
        type="bill",
        action="Pay",
        summary="Pay 84.12",
        fields=[CardField(key="amount", label="Amount", value="84.12 USD", status="sure")],
    )
    card = explain(
        Extracted(
            kind="pdf",
            text_layer="Pay 84.12 USD",
            image_bytes=None,
            page_limit_hit=True,
            source="file",
            error=None,
        ),
        FakeExplainModel(draft),
    )
    assert card.page_limit_hit is True
    assert card.fields[0].status == "sure"
