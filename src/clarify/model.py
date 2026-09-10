from __future__ import annotations

from typing import Protocol

from clarify.explain import ExplainError
from clarify.schema import Card


class ExplainModel(Protocol):
    def complete(self, *, text: str | None, image: bytes | None) -> Card: ...


class FakeExplainModel:
    def __init__(
        self,
        card: Card,
        vision_values: dict[str, str] | None = None,
        fail: str | None = None,
    ) -> None:
        self._card = card
        self.vision_values = vision_values
        self._fail = fail

    def complete(self, *, text: str | None, image: bytes | None) -> Card:
        if self._fail == "timeout":
            raise ExplainError("timeout", "model timed out")
        if self._fail == "model":
            raise ExplainError("model", "model request failed")
        return self._card


def canned_other_card() -> Card:
    """Local demo fallback when no model API key is configured (not for production)."""
    return Card(
        type="other",
        action="Review the document manually",
        summary="No model API key configured; returning a canned card for local demo.",
        warnings=["Set CLARIFY_MODEL_API_KEY (or XAI_API_KEY) for real explanations."],
        fields=[],
    )
