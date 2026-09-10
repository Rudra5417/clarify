from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

CardType = Literal[
    "bill",
    "receipt",
    "school_notice",
    "medical",
    "insurance",
    "error_screenshot",
    "draft_doc",
    "spreadsheet",
    "other",
]
FieldStatus = Literal["sure", "unsure"]


class Amount(BaseModel):
    value: float
    currency: str


class CardField(BaseModel):
    key: str
    label: str
    value: str
    status: FieldStatus = "unsure"
    reason: str | None = None


class Card(BaseModel):
    type: CardType
    sender: str | None = None
    subject: str | None = None
    amount: Amount | None = None
    deadline: date | None = None
    action: str
    summary: str
    warnings: list[str] = Field(default_factory=list)
    page_limit_hit: bool = False
    fields: list[CardField] = Field(default_factory=list)
