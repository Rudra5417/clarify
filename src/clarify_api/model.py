"""Live OpenAI-compatible model client. Lives in the API package so core stays httpx-free."""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import httpx

from clarify.explain import ExplainError
from clarify.model import ExplainModel, FakeExplainModel, canned_other_card
from clarify.schema import Card

DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"
DEFAULT_MODEL_NAME = "grok-2-vision-1212"

_SYSTEM_PROMPT = """You extract a Clarify card from a document screenshot or text.
Return ONLY a JSON object matching this schema (no markdown fences):
{
  "type": "bill|receipt|school_notice|medical|insurance|error_screenshot|draft_doc|spreadsheet|other",
  "sender": string|null,
  "subject": string|null,
  "amount": {"value": number, "currency": string}|null,
  "deadline": "YYYY-MM-DD"|null,
  "action": string,
  "summary": string,
  "warnings": [string],
  "page_limit_hit": false,
  "fields": [{"key": string, "label": string, "value": string, "status": "sure"|"unsure", "reason": string|null}]
}
Doubt by default: mark fields unsure unless clearly supported by the input.
Never invent amounts, dates, or senders that are not visible.
If the input is not a document, use type "other" and an honest summary.
"""


def resolve_model_from_env() -> ExplainModel:
    api_key = os.environ.get("CLARIFY_MODEL_API_KEY") or os.environ.get("XAI_API_KEY")
    if not api_key:
        return FakeExplainModel(canned_other_card())
    return OpenAICompatModel(api_key=api_key)


class OpenAICompatModel:
    """OpenAI-compatible chat completions client (prefer xAI when a key is set)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("CLARIFY_MODEL_API_KEY")
            or os.environ.get("XAI_API_KEY")
            or ""
        )
        env_base = os.environ.get("CLARIFY_MODEL_BASE_URL")
        resolved_base = (base_url or env_base or "").rstrip("/")
        if not resolved_base and self.api_key:
            resolved_base = DEFAULT_XAI_BASE_URL
        self.base_url = resolved_base or DEFAULT_XAI_BASE_URL
        self.model_name = (
            model_name or os.environ.get("CLARIFY_MODEL_NAME") or DEFAULT_MODEL_NAME
        )
        self.timeout = timeout

    def complete(self, *, text: str | None, image: bytes | None) -> Card:
        if not self.api_key:
            raise ExplainError("model", "missing API key")
        user_content: list[dict[str, Any]] = []
        if text:
            user_content.append({"type": "text", "text": text})
        if image:
            b64 = base64.b64encode(image).decode("ascii")
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
        if not user_content:
            user_content.append({"type": "text", "text": "(empty input)"})

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise ExplainError("timeout", "model timed out") from exc
        except httpx.HTTPError as exc:
            raise ExplainError("model", f"model request failed: {exc}") from exc

        if resp.status_code >= 500:
            raise ExplainError("timeout", "model unavailable")
        if resp.status_code >= 400:
            raise ExplainError("model", f"model HTTP {resp.status_code}")

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ExplainError("model", "invalid model response") from exc

        return _parse_card_json(content)


def _parse_card_json(content: str) -> Card:
    raw = content.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExplainError("model", "model returned non-JSON") from exc
    try:
        return Card.model_validate(obj)
    except Exception as exc:
        raise ExplainError("model", "model JSON failed card validation") from exc
