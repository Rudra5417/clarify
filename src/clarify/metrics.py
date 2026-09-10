"""Eval metrics: sure-accuracy and catch rate over Card field pairs."""

from __future__ import annotations

from pydantic import BaseModel

from clarify.schema import Card


class EvalScores(BaseModel):
    sure_accuracy: float
    catch_rate: float
    n_items: int
    n_sure_fields: int
    n_wrong_fields: int


def _norm(value: str) -> str:
    return " ".join(value.split()).strip().lower()


def score_all(pairs: list[tuple[Card, Card]]) -> EvalScores:
    n_sure = 0
    n_sure_correct = 0
    n_wrong = 0
    n_wrong_unsure = 0

    for predicted, labeled in pairs:
        label_by_key = {f.key: f for f in labeled.fields}
        for pf in predicted.fields:
            lf = label_by_key.get(pf.key)
            match = lf is not None and _norm(pf.value) == _norm(lf.value)
            if pf.status == "sure":
                n_sure += 1
                if match:
                    n_sure_correct += 1
            if not match:
                n_wrong += 1
                if pf.status == "unsure":
                    n_wrong_unsure += 1

    sure_accuracy = (n_sure_correct / n_sure) if n_sure else 0.0
    catch_rate = (n_wrong_unsure / n_wrong) if n_wrong else 0.0
    return EvalScores(
        sure_accuracy=sure_accuracy,
        catch_rate=catch_rate,
        n_items=len(pairs),
        n_sure_fields=n_sure,
        n_wrong_fields=n_wrong,
    )
