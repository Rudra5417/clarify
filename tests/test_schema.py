from clarify.schema import Card


def test_action_required_and_ignore_allowed():
    card = Card.model_validate(
        {
            "type": "other",
            "sender": None,
            "subject": None,
            "amount": None,
            "deadline": None,
            "action": "ignore",
            "summary": "This does not look like a letter, bill, or error.",
            "warnings": [],
            "page_limit_hit": False,
            "fields": [],
        }
    )
    assert card.action == "ignore"
    assert card.type == "other"


def test_amount_and_unsure_field():
    card = Card.model_validate(
        {
            "type": "bill",
            "sender": "City Water",
            "subject": "Overdue notice",
            "amount": {"value": 84.12, "currency": "USD"},
            "deadline": "2026-09-21",
            "action": "Pay $84.12 by 21 Sep",
            "summary": "They say you owe $84.12 by 21 Sep.",
            "warnings": ["overdue"],
            "page_limit_hit": False,
            "fields": [
                {
                    "key": "deadline",
                    "label": "Deadline",
                    "value": "2026-09-21",
                    "status": "unsure",
                    "reason": "two due dates",
                }
            ],
        }
    )
    assert card.amount.value == 84.12
    assert card.fields[0].status == "unsure"
