import { captureFromTab } from "./capture.js";

/** @type {object | null} */
let pendingCapture = null;

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch(() => {});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "getCapture") {
    sendResponse({ payload: pendingCapture });
    return;
  }
});

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "explain") return;

  const [tab] = await chrome.tabs.query({
    active: true,
    currentWindow: true,
  });
  if (!tab?.id) return;

  try {
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch {
    // Side panel may already be open.
  }

  let payload;
  try {
    payload = await captureFromTab(tab.id);
  } catch {
    payload = { kind: "none", fallback: false };
  }

  pendingCapture = payload;
  chrome.runtime.sendMessage({ type: "capture", payload }).catch(() => {});
});
