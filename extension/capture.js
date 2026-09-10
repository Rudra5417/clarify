/** @param {{ pdfUrl?: string, imageUrl?: string, selection?: string, visibleText?: string }} input */
export function pickCapture({ pdfUrl, imageUrl, selection, visibleText }) {
  if (pdfUrl) {
    return { kind: "pdf", fallback: false, url: pdfUrl };
  }
  if (imageUrl) {
    return { kind: "image", fallback: false, url: imageUrl };
  }
  if (selection) {
    return { kind: "text", fallback: false, text: selection };
  }
  if (visibleText) {
    return {
      kind: "text",
      fallback: true,
      text: String(visibleText).slice(0, 4000),
    };
  }
  return { kind: "none", fallback: false };
}

function pageProbe() {
  const selection = String(window.getSelection?.()?.toString?.() ?? "").trim();
  const visibleText = String(document.body?.innerText ?? "").trim();
  const contentType = document.contentType || "";
  const img = document.querySelector("img");
  const imageUrl = img?.currentSrc || img?.src || "";
  return { selection, visibleText, contentType, imageUrl };
}

/**
 * Read the active tab and return a pickCapture result.
 * @param {number} tabId
 */
export async function captureFromTab(tabId) {
  const tab = await chrome.tabs.get(tabId);
  const tabUrl = tab.url || "";

  let probe = {
    selection: "",
    visibleText: "",
    contentType: "",
    imageUrl: "",
  };

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: pageProbe,
    });
    if (results && results[0] && results[0].result) {
      probe = results[0].result;
    }
  } catch {
    // Restricted pages (chrome://, PDF viewer chrome internals, etc.)
  }

  const isPdfUrl = /\.pdf($|\?)/i.test(tabUrl);
  const isPdfType = /application\/pdf/i.test(probe.contentType || "");
  const pdfUrl = isPdfUrl || isPdfType ? tabUrl : "";

  let imageUrl = "";
  if (!pdfUrl) {
    if (/\.(png|jpe?g|webp)($|\?)/i.test(tabUrl)) {
      imageUrl = tabUrl;
    } else if (probe.imageUrl) {
      imageUrl = probe.imageUrl;
    }
  }

  return pickCapture({
    pdfUrl,
    imageUrl,
    selection: probe.selection || "",
    visibleText: probe.visibleText || "",
  });
}
