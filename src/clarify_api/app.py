"""FastAPI app: POST /v1/explain, GET /v1/eval, and GET /health."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from clarify.explain import ExplainError, explain
from clarify.extract import Extracted, extract_image, extract_pdf, extract_text
from clarify.model import ExplainModel
from clarify_api.privacy import get_privacy_logger, log_explain_event

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
_IMAGE_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/webp", "image/")
_EVAL_DIR = Path(__file__).resolve().parents[2] / "eval"


def create_app(model: ExplainModel) -> FastAPI:
    app = FastAPI(title="clarify")
    logger = get_privacy_logger()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/eval")
    def v1_eval() -> dict[str, Any]:
        baseline_path = _EVAL_DIR / "baseline.json"
        labels_path = _EVAL_DIR / "labels.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        out = dict(baseline)
        out["n_items"] = len(labels)
        return out

    @app.post("/v1/explain")
    async def v1_explain(request: Request) -> Any:
        started = time.perf_counter()
        error_code: str | None = None
        card_type: str | None = None
        try:
            extracted = await _extract_from_request(request)
            card = explain(extracted, model)
            card_type = card.type
            return {"card": card.model_dump(mode="json")}
        except ExplainError as exc:
            error_code = exc.code
            if exc.code == "timeout":
                return JSONResponse(
                    status_code=503,
                    content={"error": "timeout", "message": "retry"},
                )
            if exc.code in ("empty", "oversize"):
                return JSONResponse(
                    status_code=400,
                    content={"error": exc.code, "message": exc.message},
                )
            return JSONResponse(
                status_code=500,
                content={"error": exc.code, "message": exc.message},
            )
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            log_explain_event(
                logger,
                error=error_code,
                latency_ms=latency_ms,
                card_type=card_type,
            )

    return app


async def _extract_from_request(request: Request) -> Extracted:
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        body = await request.json()
        if not isinstance(body, dict):
            raise ExplainError("empty", "empty")
        text = body.get("text")
        if text is None or (isinstance(text, str) and text == ""):
            raise ExplainError("empty", "empty")
        fallback = bool(body.get("fallback", False))
        return extract_text(str(text), fallback=fallback)

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            raise ExplainError("empty", "empty")
        if isinstance(upload, UploadFile):
            data = await upload.read()
            filename = upload.filename or ""
            file_type = upload.content_type or ""
        elif isinstance(upload, (bytes, bytearray)):
            data = bytes(upload)
            filename = ""
            file_type = ""
        else:
            raise ExplainError("empty", "empty")
        return _extract_file(data, filename, file_type)

    raise ExplainError("empty", "empty")


def _extract_file(data: bytes, filename: str, content_type: str) -> Extracted:
    name = filename.lower()
    ctype = content_type.lower()
    if ctype == "application/pdf" or name.endswith(".pdf"):
        return extract_pdf(data)
    if any(ctype.startswith(t) for t in _IMAGE_TYPES) or name.endswith(_IMAGE_SUFFIXES):
        return extract_image(data)
    return extract_image(data)
