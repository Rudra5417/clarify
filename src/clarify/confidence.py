from dataclasses import dataclass
from typing import Literal

from clarify.schema import Card, CardField

Source = Literal["file", "selection", "visible_fallback"]


@dataclass(frozen=True)
class Evidence:
    text_layer: str | None
    vision_values: dict[str, str] | None
    source: Source


def _literally_present(value: str, text: str) -> bool:
    return value.strip() != "" and value.strip() in text


def apply_confidence(card: Card, evidence: Evidence) -> Card:
    fields: list[CardField] = []
    for field in card.fields:
        status, reason = _status_for(field, evidence)
        fields.append(field.model_copy(update={"status": status, "reason": reason}))
    return card.model_copy(update={"fields": fields})


def _status_for(field: CardField, evidence: Evidence) -> tuple[str, str | None]:
    if evidence.source == "visible_fallback":
        return "unsure", "visible text fallback"
    if evidence.text_layer is None and evidence.vision_values is None:
        return "unsure", "cannot check"

    value = field.value
    in_text = evidence.text_layer is not None and _literally_present(value, evidence.text_layer)
    vision = (
        evidence.vision_values.get(field.key)
        if evidence.vision_values is not None
        else None
    )

    if evidence.text_layer is not None and vision is not None:
        if vision != value:
            return "unsure", "text and vision disagree"
        if not in_text:
            return "unsure", "not on page"
        return "sure", None

    if evidence.text_layer is not None:
        if in_text:
            return "sure", None
        return "unsure", "not on page"

    if vision is None:
        return "unsure", "cannot check"
    if vision != value:
        return "unsure", "text and vision disagree"
    return "sure", None
