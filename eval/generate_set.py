"""Generate the frozen 40-item eval set, fake predictions, and baseline."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from clarify.metrics import score_all
from clarify.schema import Card, CardField

ROOT = Path(__file__).resolve().parent
ITEMS = ROOT / "items"


def _bill(i: int) -> tuple[str, str, Card]:
    name = f"bill_{i:02d}.txt"
    amount = f"{20 + i}.50 USD"
    due = f"2026-{(i % 12) + 1:02d}-15"
    sender = f"Utility Co {i}"
    body = (
        f"From: {sender}\n"
        f"Subject: Monthly bill #{i}\n"
        f"Amount due: {amount}\n"
        f"Due date: {due}\n"
        f"Please pay by the due date.\n"
    )
    card = Card(
        type="bill" if i % 3 else "school_notice",
        sender=sender,
        subject=f"Monthly bill #{i}",
        action=f"Pay {amount}",
        summary=f"Pay {amount} to {sender} by {due}.",
        fields=[
            CardField(key="amount", label="Amount", value=amount),
            CardField(key="deadline", label="Deadline", value=due),
            CardField(key="sender", label="Sender", value=sender),
        ],
    )
    return name, body, card


def _notice(i: int) -> tuple[str, str, Card]:
    name = f"notice_{i:02d}.txt"
    sender = f"City Office {i}"
    deadline = f"2026-{(i % 9) + 1:02d}-01"
    body = (
        f"NOTICE from {sender}\n"
        f"School / municipal notice #{i}\n"
        f"Please respond by {deadline}.\n"
        f"Bring forms to the front desk.\n"
    )
    card = Card(
        type="school_notice",
        sender=sender,
        subject=f"Notice #{i}",
        action=f"Respond by {deadline}",
        summary=f"Respond to {sender} by {deadline}.",
        fields=[
            CardField(key="deadline", label="Deadline", value=deadline),
            CardField(key="sender", label="Sender", value=sender),
        ],
    )
    return name, body, card


def _receipt(i: int) -> tuple[str, str, Card]:
    name = f"receipt_{i:02d}.txt"
    amount = f"{8 + i}.99 USD"
    store = f"Corner Mart {i}"
    body = (
        f"{store}\n"
        f"RECEIPT\n"
        f"Total: {amount}\n"
        f"Thank you for shopping.\n"
    )
    card = Card(
        type="receipt",
        sender=store,
        action="Keep for records",
        summary=f"Receipt from {store} for {amount}.",
        fields=[
            CardField(key="amount", label="Amount", value=amount),
            CardField(key="sender", label="Store", value=store),
        ],
    )
    return name, body, card


def _error(i: int) -> tuple[str, str, Card]:
    name = f"error_{i:02d}.txt"
    code = f"ERR-{1000 + i}"
    body = (
        f"[Error dialog screenshot stand-in]\n"
        f"Title: Something went wrong\n"
        f"Code: {code}\n"
        f"Message: Unable to complete the request. Try again later.\n"
        f"Buttons: [Retry] [Cancel]\n"
    )
    card = Card(
        type="error_screenshot",
        subject=f"Error {code}",
        action="Retry or cancel",
        summary=f"App error {code}: unable to complete the request.",
        fields=[
            CardField(key="error_code", label="Error code", value=code),
            CardField(key="message", label="Message", value="Unable to complete the request. Try again later."),
        ],
    )
    return name, body, card


def _doc_snippet() -> tuple[str, str, Card]:
    name = "doc_snippet.txt"
    body = (
        "Draft: Q3 planning notes\n"
        "Owner: Alex Rivera\n"
        "Status: Needs review before Friday.\n"
        "Action items: finalize budget, send invite.\n"
    )
    card = Card(
        type="draft_doc",
        sender="Alex Rivera",
        subject="Q3 planning notes",
        action="Review before Friday",
        summary="Draft doc needs review before Friday; finalize budget and send invite.",
        fields=[
            CardField(key="owner", label="Owner", value="Alex Rivera"),
            CardField(key="deadline", label="Deadline", value="Friday"),
        ],
    )
    return name, body, card


def _sheet() -> tuple[str, str, Card]:
    name = "sheet.csv"
    body = "item,qty,cost\npaper,2,12.00\nink,1,24.50\ntotal,,36.50\n"
    card = Card(
        type="spreadsheet",
        action="Check total 36.50",
        summary="Spreadsheet range totals 36.50 across paper and ink.",
        fields=[
            CardField(key="amount", label="Total", value="36.50"),
            CardField(key="rows", label="Rows", value="3"),
        ],
    )
    return name, body, card


def build_items() -> list[dict]:
    """Return 40 label records: id, file, type, card."""
    records: list[dict] = []

    # 34 bills/notices (20 bills + 14 notices)
    for i in range(1, 21):
        fname, body, card = _bill(i)
        records.append({"id": fname.replace(".txt", ""), "file": f"items/{fname}", "body": body, "card": card})
    for i in range(1, 15):
        fname, body, card = _notice(i)
        records.append({"id": fname.replace(".txt", ""), "file": f"items/{fname}", "body": body, "card": card})

    for i in range(1, 3):
        fname, body, card = _receipt(i)
        records.append({"id": fname.replace(".txt", ""), "file": f"items/{fname}", "body": body, "card": card})

    for i in range(1, 3):
        fname, body, card = _error(i)
        records.append({"id": fname.replace(".txt", ""), "file": f"items/{fname}", "body": body, "card": card})

    fname, body, card = _doc_snippet()
    records.append({"id": "doc_snippet", "file": f"items/{fname}", "body": body, "card": card})

    fname, body, card = _sheet()
    records.append({"id": "sheet", "file": f"items/{fname}", "body": body, "card": card})

    assert len(records) == 40, len(records)
    return records


def fake_predictions(labels: list[dict], flip_count: int = 10) -> list[dict]:
    """Copy each label card; on first flip_count items, flip one field to wrong+unsure."""
    preds: list[dict] = []
    for idx, rec in enumerate(labels):
        card = deepcopy(rec["card"])
        fields = [
            CardField(key=f.key, label=f.label, value=f.value, status="sure")
            for f in card.fields
        ]
        if idx < flip_count and fields:
            wrong = fields[0]
            fields[0] = CardField(
                key=wrong.key,
                label=wrong.label,
                value=f"WRONG-{wrong.value}",
                status="unsure",
                reason="synthetic flip for catch_rate",
            )
        predicted = card.model_copy(update={"fields": fields})
        preds.append({"id": rec["id"], "card": predicted})
    return preds


def main() -> None:
    ITEMS.mkdir(parents=True, exist_ok=True)
    records = build_items()

    labels_out = []
    for rec in records:
        path = ROOT / rec["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rec["body"], encoding="utf-8")
        labels_out.append(
            {
                "id": rec["id"],
                "file": rec["file"],
                "type": rec["card"].type,
                "card": rec["card"].model_dump(mode="json"),
            }
        )

    (ROOT / "labels.json").write_text(
        json.dumps(labels_out, indent=2) + "\n",
        encoding="utf-8",
    )

    label_cards = [{"id": r["id"], "card": r["card"]} for r in records]
    preds = fake_predictions(label_cards, flip_count=10)
    preds_out = [{"id": p["id"], "card": p["card"].model_dump(mode="json")} for p in preds]
    (ROOT / "predictions.json").write_text(
        json.dumps(preds_out, indent=2) + "\n",
        encoding="utf-8",
    )

    pairs = [(p["card"], r["card"]) for p, r in zip(preds, records)]
    scores = score_all(pairs)
    baseline = {
        "sure_accuracy": scores.sure_accuracy,
        "catch_rate": scores.catch_rate,
        "n_items": scores.n_items,
        "n_sure_fields": scores.n_sure_fields,
        "n_wrong_fields": scores.n_wrong_fields,
        "note": "frozen FakeExplainModel-style sweep: correct+sure except 10 items with one wrong+unsure field",
    }
    (ROOT / "baseline.json").write_text(
        json.dumps(baseline, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(records)} items; baseline={baseline}")


if __name__ == "__main__":
    main()
