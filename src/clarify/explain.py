from typing import TYPE_CHECKING

from clarify.confidence import Evidence, apply_confidence
from clarify.extract import Extracted
from clarify.schema import Card

if TYPE_CHECKING:
    from clarify.model import ExplainModel


class ExplainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def unreadable_card(*, page_limit_hit: bool = False) -> Card:
    return Card(
        type="other",
        action="ignore",
        summary="We could not read this document. All fields are unsure.",
        page_limit_hit=page_limit_hit,
        fields=[],
    )


def explain(extracted: Extracted, model: "ExplainModel") -> Card:
    if extracted.error in ("empty", "oversize"):
        raise ExplainError(extracted.error, extracted.error)
    if extracted.error == "unreadable":
        return unreadable_card(page_limit_hit=extracted.page_limit_hit)
    if extracted.error:
        raise ExplainError(extracted.error, extracted.error)

    card = model.complete(text=extracted.text_layer, image=extracted.image_bytes)
    card = card.model_copy(update={"page_limit_hit": extracted.page_limit_hit})
    vision_values = getattr(model, "vision_values", None)
    evidence = Evidence(
        text_layer=extracted.text_layer,
        vision_values=vision_values,
        source=extracted.source,
    )
    return apply_confidence(card, evidence)
