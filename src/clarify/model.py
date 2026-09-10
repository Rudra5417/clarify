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
        return self._card
