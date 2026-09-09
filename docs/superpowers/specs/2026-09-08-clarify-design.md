# Clarify v1 Design

One-shot reader for whatever is already on screen. Open a PDF, image, Google Doc, or sheet in Chrome, press a shortcut, get a card: what it is, what it means, what to do, which fields might be wrong.

**Working name:** Clarify (rename later; do not bikeshed in v1).  
**Repo root:** `C:\Users\rudi.patel\clarify`  
**Primary goal:** portfolio proof for an **AI product engineer** role — not a startup, not a file locker, not a chatbot.  
**Success:** a stranger can try a public drop page; you can run the extension locally; a hiring manager understands the product from one post in 20 seconds.

## 1. Purpose

Chat-with-a-PDF hides when the model is wrong. Clarify puts the model **next to the document the user is already reading** and defaults to doubt.

**Primary user:** anyone staring at a letter, bill, receipt, error screenshot, or a selected range in a Doc/Sheet who wants a plain-language read plus a next step.

**Hiring-manager user:** someone who should see: not a chat box, the model can be wrong and the UI still works, you measured it, you wrote about it.

## 2. Non-goals (v1)

- Mac menu bar, Finder, Windows Explorer, native overlay
- Dropbox-style library, sync, folders, search, history
- Accounts, login, payments, user file storage
- Google OAuth, Drive, Gmail, Workspace APIs
- Chat / follow-up prompt box
- Reading an entire long contract or whole workbook
- Formula repair across sheets
- Agent frameworks, vector DB, RAG
- Training on user uploads
- Receipt-only IDP / competing with Mindee
- Markets terminal / finance product (separate repo; out of scope)

## 3. Product surfaces

| Surface | Role |
|---|---|
| Chrome extension (MV3) side panel | The product. Hotkey `Ctrl+Shift+E` (customizable later; this is the v1 default). |
| Public drop page | Trailer for LinkedIn/X. Same API, drag-and-drop a file, same card. No extension required to try. |
| Public eval page | Field accuracy when we said sure, catch rate on mistakes, cost, latency, on a frozen 40-item set. |
| Local API | Brain. Keys never live in the extension. |

### Capture order (extension)

On hotkey, try in order; stop at the first that works:

1. PDF in this tab → send the PDF (**first 2 pages** only; if longer, card includes a warning).
2. Image tab or a primary `<img>` on the page → send that image.
3. Current **text selection** (Docs, Sheets, or any page) → send selection as text, or as a table if it looks like rows/cells.
4. If selection is empty → visible text in the tab, **hard-capped** (first ~4k characters). Mark all extracted fields **unsure** if we used this fallback.
5. If none of that works → side panel shows a drop zone.

No Drive picker. No “open from Google.”

### Side panel layout (top → bottom)

1. **What this is** — one line: type · sender or app name  
2. **In plain language** — 2–4 sentences  
3. **Do this** — one primary action, or `ignore`  
4. **Warnings** — overdue, denied, `#REF!`, possible scam; omit section if empty  
5. **Fields** — name, value, sure/unsure. Unsure is visually marked. Any field is editable.  
6. **Looks right** / keep edits — records a correction **only on the author’s golden-set flow**, not on public demo uploads.

No prompt box. No “ask a follow-up.” If a follow-up is needed, the schema failed; tighten the schema.

Same layout for a utility bill and for an error screenshot. Only the field values change.

## 4. Schema

One JSON card for every run. Extra values may be null.

```json
{
  "type": "bill | receipt | school_notice | medical | insurance | error_screenshot | draft_doc | spreadsheet | other",
  "sender": "string | null",
  "subject": "string | null",
  "amount": { "value": 84.12, "currency": "USD" } | null,
  "deadline": "YYYY-MM-DD | null",
  "action": "string",
  "summary": "string",
  "warnings": ["string"],
  "page_limit_hit": false,
  "fields": [
    {
      "key": "amount",
      "label": "Amount",
      "value": "84.12 USD",
      "status": "sure | unsure",
      "reason": "string | null"
    }
  ]
}
```

`action` is required. Use `"ignore"` when there is nothing to do.  
`type: other` plus a summary that says it is not a letter/bill/error is valid (cat photo, meme).

Do **not** add per-type schemas in v1.

## 5. Sure vs unsure

Confidence is not a model-said percentage. Default is **unsure**.

A field is **sure** only if all of the following hold:

- The value is literally present in the provided text or on the provided page(s).
- Independent checks agree when both exist (e.g. PDF text layer vs vision).
- There are not two conflicting values for that field.

A field is **unsure** if any of:

- Missing, unreadable, or inferred (not printed).
- Two values conflict.
- Text-layer extract and vision disagree.
- We used the “visible text fallback” (no explicit selection).
- We cannot run a check.

If the whole document is unreadable, **every** field is unsure and `summary` says we could not read it. Never green-tick a guess.

`reason` on unsure fields is a short human string (`"two due dates"`, `"not on page"`, `"blurry"`). Shown in the UI as secondary text, not as a chat.

## 6. Architecture

```
Chrome extension                    Public drop page
  capture (pdf/image/selection)       file upload
           \                         /
            \                       /
             v                     v
              POST /v1/explain
              (multipart file or JSON text)
                      |
                      v
              Clarify API (Python)
                1. reject oversize / empty
                2. PDF: first 2 pages; if text layer exists, extract (Docling or pypdf)
                3. image: vision
                4. selection: text/table as-is
                5. model: structured JSON matching section 4
                6. sure/unsure pass (rules in section 5)
                7. return card; discard payload
```

**One write path:** `POST /v1/explain`.  
**One eval path:** `GET /v1/eval` returns the frozen golden-set metrics (computed offline or on demand from checked-in labels, not from live user uploads).

### Stack

| Piece | Choice |
|---|---|
| Extension | Chrome MV3, side panel |
| API | Python FastAPI |
| PDF text | Docling if available; otherwise pypdf. Vision if no usable text. |
| Model | Vision-capable LLM with **structured JSON** output. Prefer xAI if a key is present; otherwise any OpenAI-compatible vision endpoint via env. |
| Public demo | Same API, rate-limited. Local-first; host only when posting. |
| Storage | None for user files. Golden set is files **in the repo** under `eval/`. |

The extension stores only `apiBaseUrl` (default `http://127.0.0.1:8788`). No model keys in the client.

### Size and limits

- PDF: first 2 pages. `page_limit_hit: true` if the file has more.
- Image: one image, max 10 MB. Reject above cap with an error card.
- Selection: send as text; if it looks like TSV/CSV, pass as a table blob.
- Visible-text fallback: 4000 characters, all fields unsure.
- Timeout: API returns an error card (see §7). Do not return a partial invented bill.

## 7. Failures

Always a card or a named error. Never a fake explanation.

| Condition | Response |
|---|---|
| Nothing captured | Panel: “Select text or drop a file.” No API call. |
| Empty / oversize | HTTP 400 + panel error. |
| Blurry / unreadable | 200 + card; summary says unreadable; all fields `unsure`. |
| Model timeout / down | HTTP 503 + “retry”; empty card; no invented fields. |
| Long PDF | 200 + card for pages 1–2; `page_limit_hit: true`; warning in UI. |
| Not a document | 200 + `type: other` + honest summary. |

## 8. Privacy

- No accounts.
- User payload is processed in memory and **not written** to disk on the server.
- Do not log file bytes, filenames that look like PII, or extracted field values from public demo traffic.
- Allowed logs: timestamp, `type` if returned, latency, token/cost estimate, error code.
- Public demo: rate limit; discard after response.
- Golden-set corrections are **author-only**, checked into `eval/`. Strangers on the drop page do not train anything.

## 9. Eval

**Set:** 40 labeled examples in `eval/items/` plus `eval/labels.json`. Mix:

- everyday notices / bills (majority)
- 1–2 receipts
- 1–2 error screenshots
- 1 Google Doc-style snippet (plain text)
- 1 small spreadsheet range (CSV/TSV)

Labels use the same schema as §4. Collected by the author; no user uploads in the set.

**Metrics (eval page and posts):**

1. **Field accuracy given sure** — among fields we marked `sure`, fraction that match the label.  
2. **Catch rate** — among fields we got wrong, fraction we marked `unsure`. This is the headline metric.  
3. **Cost per run** and **p50/p95 latency**.

Do not post a single “accuracy 99%” number. The story is: when we were sure, were we right; when we were wrong, did we admit it.

## 10. Public posts

Three posts after the two-week cut works:

1. Problem: chat-with-a-PDF hides errors. Side panel + yellow fields.  
2. Numbers: the 40-item score, including failures.  
3. 30s demo: open a PDF, hotkey, unsure field, fix it.

Demo URL = public drop page. Repo is public. Extension can stay unpacked/local for v1; Chrome Web Store is **not** required to be done.

## 11. Two-week cut

**Must ship**

- Extension: hotkey, side panel, capture order in §3  
- `POST /v1/explain` + sure/unsure pass  
- Public drop page (same card UI)  
- 40-item golden set + eval page  
- README: doubt-by-default, 2-page cap, privacy  

**Done means:** stranger can try the drop page; you can run the extension against localhost; one post can be written from the eval page.

Anything in §2 is a new request, not a stretch goal sneaked into week two.

## 12. Testing

- Unit: sure/unsure rules (conflict, missing, text-vs-vision disagree, fallback ⇒ all unsure).  
- API: fixture PDF (text layer), fixture image, empty body, oversize, page_limit_hit.  
- Extension: capture order with mocked tab (PDF URL, selection, empty → drop zone).  
- Eval script: rerun the 40 items, fail CI if catch rate or sure-accuracy regresses below the last committed baseline in `eval/baseline.json`.

No live model calls in unit tests. Fixtures + recorded model JSON for API tests.
