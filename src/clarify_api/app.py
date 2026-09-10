"""FastAPI app: POST /v1/explain, GET /v1/eval, GET /health, and static web/."""

from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile

from clarify.explain import ExplainError, explain
from clarify.extract import Extracted, extract_image, extract_pdf, extract_text
from clarify.model import ExplainModel
from clarify_api.model import resolve_model_from_env
from clarify_api.privacy import get_privacy_logger, log_explain_event

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
_IMAGE_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/webp", "image/")
_ROOT = Path(__file__).resolve().parents[2]
_EVAL_DIR = _ROOT / "eval"
_WEB_DIR = _ROOT / "web"
_LOCALHOST_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class IpRateLimiter:
    """In-memory sliding-window limiter: max_requests per window_seconds per IP."""

    def __init__(self, max_requests: int = 30, window_seconds: float = 3600.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, ip: str) -> bool:
        if ip in _LOCALHOST_HOSTS:
            return True
        now = time.monotonic()
        q = self._hits[ip]
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= self.max_requests:
            return False
        q.append(now)
        return True


def _host_is_localhost(request: Request) -> bool:
    host = request.headers.get("host") or ""
    hostname = host.split("%", 1)[0].split(":", 1)[0].strip().lower()
    if hostname.startswith("[") and hostname.endswith("]"):
        hostname = hostname[1:-1]
    return hostname in _LOCALHOST_HOSTS


def create_app(model: ExplainModel | None = None) -> FastAPI:
    if model is None:
        model = resolve_model_from_env()

    app = FastAPI(title="clarify")
    logger = get_privacy_logger()
    limiter = IpRateLimiter(max_requests=30, window_seconds=3600.0)

    def enforce_explain_rate_limit(request: Request) -> None:
        # Local drop page / demo: Host 127.0.0.1 is unlimited.
        if _host_is_localhost(request):
            return
        ip = request.client.host if request.client else ""
        if not limiter.allow(ip):
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limit", "message": "too many requests"},
            )

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
    async def v1_explain(
        request: Request,
        _: None = Depends(enforce_explain_rate_limit),
    ) -> Any:
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
            if exc.code in ("timeout", "model"):
                return JSONResponse(
                    status_code=503,
                    content={"error": exc.code, "message": "retry"},
                )
            if exc.code in ("empty", "oversize"):
                return JSONResponse(
                    status_code=400,
                    content={"error": exc.code, "message": exc.message},
                )
            return JSONResponse(
                status_code=503,
                content={"error": exc.code, "message": "retry"},
            )
        finally:
            latency_ms = (time.perf_counter() - started) * 1000
            log_explain_event(
                logger,
                error=error_code,
                latency_ms=latency_ms,
                card_type=card_type,
            )

    @app.get("/eval")
    def eval_page() -> FileResponse:
        # StaticFiles(html=True) only auto-serves index.html / 404.html, not eval.html.
        return FileResponse(_WEB_DIR / "eval.html")

    # Mount after /v1 (and /eval) routes so those paths stay authoritative.
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web")
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
