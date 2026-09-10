# tests/test_api.py
from fastapi.testclient import TestClient
from clarify.model import FakeExplainModel
from clarify.schema import Card, CardField
from clarify_api.app import create_app
from tests.fixtures.make_pdf import pdf_with_n_pages, pdf_with_text


def _client(model=None) -> TestClient:
    draft = Card(
        type="bill",
        sender="City Water",
        action="Pay 84.12 USD",
        summary="Pay the water bill.",
        fields=[CardField(key="amount", label="Amount", value="84.12 USD")],
    )
    app = create_app(model or FakeExplainModel(draft))
    return TestClient(app)


def test_empty_body_400():
    r = _client().post("/v1/explain")
    assert r.status_code == 400
    assert r.json()["error"] in {"empty", "oversize"}


def test_oversize_image_400():
    r = _client().post("/v1/explain", files={"file": ("x.bin", b"x" * (10 * 1024 * 1024 + 1), "application/octet-stream")})
    assert r.status_code == 400
    assert r.json()["error"] == "oversize"


def test_timeout_503_no_card():
    app = create_app(FakeExplainModel(Card(type="other", action="ignore", summary="x"), fail="timeout"))
    r = TestClient(app).post("/v1/explain", json={"text": "hello", "fallback": False})
    assert r.status_code == 503
    assert "card" not in r.json()
    assert r.json()["error"] == "timeout"


def test_pdf_text_200_and_page_limit():
    draft = Card(
        type="bill",
        action="Pay 84.12 USD",
        summary="Pay the water bill 84.12 USD",
        fields=[CardField(key="amount", label="Amount", value="84.12 USD")],
    )
    c = _client(FakeExplainModel(draft))
    r = c.post("/v1/explain", files={"file": ("bill.pdf", pdf_with_text("Pay 84.12 USD"), "application/pdf")})
    assert r.status_code == 200
    assert r.json()["card"]["fields"][0]["status"] == "sure"

    r2 = c.post("/v1/explain", files={"file": ("long.pdf", pdf_with_n_pages(3), "application/pdf")})
    assert r2.status_code == 200
    assert r2.json()["card"]["page_limit_hit"] is True


def test_eval_endpoint():
    r = _client().get("/v1/eval")
    assert r.status_code == 200
    body = r.json()
    assert body["n_items"] == 40
    assert "sure_accuracy" in body
    assert "catch_rate" in body


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200


def test_rate_limiter_unit():
    from clarify_api.app import IpRateLimiter

    limiter = IpRateLimiter(max_requests=30, window_seconds=3600)
    for _ in range(30):
        assert limiter.allow("1.2.3.4") is True
    assert limiter.allow("1.2.3.4") is False
    assert limiter.allow("127.0.0.1") is True


def test_rate_limit_skips_localhost():
    app = create_app(FakeExplainModel(Card(type="other", action="ignore", summary="x")))
    c = TestClient(app)
    for _ in range(35):
        r = c.post(
            "/v1/explain",
            json={"text": "hello", "fallback": False},
            headers={"Host": "127.0.0.1:8788"},
        )
        assert r.status_code == 200


def test_create_app_no_key_boots(monkeypatch):
    monkeypatch.delenv("CLARIFY_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    app = create_app()
    r = TestClient(app).get("/health")
    assert r.status_code == 200
    r2 = TestClient(app).post("/v1/explain", json={"text": "hello", "fallback": False})
    assert r2.status_code == 200
    assert r2.json()["card"]["type"] == "other"
