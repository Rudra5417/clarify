import { renderCard } from "./card.js";

const DEFAULT_API = "http://127.0.0.1:8788";

const drop = document.getElementById("drop");
const fileInput = document.getElementById("file");
const errorEl = document.getElementById("error");
const statusEl = document.getElementById("status");
const root = document.getElementById("card-root");

function showError(msg) {
  errorEl.hidden = !msg;
  errorEl.textContent = msg || "";
}

function showStatus(msg) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg || "";
}

function showDropZone(visible) {
  drop.hidden = !visible;
}

async function getApiBaseUrl() {
  const stored = await chrome.storage.local.get("apiBaseUrl");
  return stored.apiBaseUrl || DEFAULT_API;
}

async function postExplain(init) {
  const apiBaseUrl = await getApiBaseUrl();
  let res;
  try {
    res = await fetch(`${apiBaseUrl}/v1/explain`, init);
  } catch {
    showError("Could not reach the API.");
    return;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    showError(body.message || body.error || `Request failed (${res.status})`);
    return;
  }
  if (!body.card) {
    showError("No card in response.");
    return;
  }
  showError("");
  showDropZone(false);
  renderCard(root, body.card);
}

async function explainText(text, fallback) {
  showStatus("Explaining…");
  root.innerHTML = "";
  await postExplain({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, fallback: Boolean(fallback) }),
  });
  showStatus("");
}

async function explainFile(file) {
  showStatus("Explaining…");
  root.innerHTML = "";
  const formData = new FormData();
  formData.append("file", file, file.name);
  await postExplain({ method: "POST", body: formData });
  showStatus("");
}

async function explainUrl(url, kind) {
  showStatus("Fetching…");
  root.innerHTML = "";
  let blob;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("fetch failed");
    blob = await res.blob();
  } catch {
    showStatus("");
    showError("");
    showDropZone(true);
    return;
  }
  const name =
    kind === "pdf"
      ? "document.pdf"
      : url.split("/").pop()?.split("?")[0] || "image.png";
  const file = new File([blob], name, {
    type: blob.type || (kind === "pdf" ? "application/pdf" : "image/png"),
  });
  await explainFile(file);
}

async function handleCapture(payload) {
  showError("");
  showStatus("");
  root.innerHTML = "";

  if (!payload || payload.kind === "none") {
    showDropZone(true);
    return;
  }

  showDropZone(false);

  if (payload.kind === "text") {
    await explainText(payload.text || "", payload.fallback);
    return;
  }

  if (payload.kind === "pdf" || payload.kind === "image") {
    if (!payload.url) {
      showDropZone(true);
      return;
    }
    await explainUrl(payload.url, payload.kind);
    return;
  }

  showDropZone(true);
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "capture") {
    handleCapture(msg.payload);
  }
});

chrome.runtime.sendMessage({ type: "getCapture" }, (res) => {
  if (chrome.runtime.lastError) return;
  if (res && res.payload) handleCapture(res.payload);
  else showDropZone(true);
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files && fileInput.files[0];
  if (file) explainFile(file);
});

drop.addEventListener("dragover", (e) => {
  e.preventDefault();
});
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  const file =
    e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
  if (file) explainFile(file);
});
