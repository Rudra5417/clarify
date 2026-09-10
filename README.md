# Clarify

One-shot reader for whatever is already on screen. Chrome shortcut → what this is, what to do, which fields might be wrong.

Not a chatbot. Not a file locker. No Drive login. No native apps.

**Design spec:** [docs/superpowers/specs/2026-09-08-clarify-design.md](docs/superpowers/specs/2026-09-08-clarify-design.md)

## Product rules

- **Doubt-by-default:** fields are `unsure` unless evidence clearly supports them.
- **PDF cap:** first **2 pages** only; longer files set `page_limit_hit`.
- **Image cap:** **10 MB** max; oversize is rejected.

## Privacy

- No accounts.
- Uploads are processed in memory and **not stored** on the server.
- Logs are **type / latency / error only** — never file bytes or field values.
- Public/demo `POST /v1/explain` is rate-limited (**30/hour/IP**); **localhost is unlimited**.

## Run locally

```bash
pip install -e ".[dev]"
python -m clarify_api
```

API + drop page: [http://127.0.0.1:8788/](http://127.0.0.1:8788/)  
Eval page: [http://127.0.0.1:8788/eval](http://127.0.0.1:8788/eval)

### Real model (optional)

Tests never need a model key. For real explanations, set:

```bash
# Prefer xAI (default base https://api.x.ai/v1 when a key is set)
set CLARIFY_MODEL_API_KEY=your_key
# optional overrides:
# set CLARIFY_MODEL_BASE_URL=https://api.x.ai/v1
# set CLARIFY_MODEL_NAME=grok-2-vision-1212
# or: set XAI_API_KEY=your_key
```

If no key is set, the API boots with a canned `type=other` fake card for local UI work (not for production).

## Chrome extension (unpacked)

Chrome Web Store is **not** required.

1. Open `chrome://extensions`
2. Enable Developer mode
3. **Load unpacked** → select the `extension/` folder
4. Hotkey: **Ctrl+Shift+E** (opens the side panel and captures the active tab)

The extension talks to `http://127.0.0.1:8788` by default. No model keys in the client.

## Tests

```bash
pytest -q
node tests/test_card.mjs
node tests/test_capture.mjs
```
