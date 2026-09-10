// tests/test_capture.mjs
import { pickCapture } from "../extension/capture.js";

function eq(a, b) {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error(`expected ${JSON.stringify(b)} got ${JSON.stringify(a)}`);
  }
}
eq(pickCapture({ pdfUrl: "https://x/a.pdf", imageUrl: "https://x/a.png", selection: "sel", visibleText: "vis" }), { kind: "pdf", fallback: false, url: "https://x/a.pdf" });
eq(pickCapture({ pdfUrl: "", imageUrl: "https://x/a.png", selection: "sel", visibleText: "vis" }), { kind: "image", fallback: false, url: "https://x/a.png" });
eq(pickCapture({ pdfUrl: "", imageUrl: "", selection: "hello", visibleText: "vis" }), { kind: "text", fallback: false, text: "hello" });
eq(pickCapture({ pdfUrl: "", imageUrl: "", selection: "", visibleText: "x".repeat(5000) }).text.length, 4000);
eq(pickCapture({ pdfUrl: "", imageUrl: "", selection: "", visibleText: "x".repeat(5000) }).fallback, true);
eq(pickCapture({ pdfUrl: "", imageUrl: "", selection: "", visibleText: "" }), { kind: "none", fallback: false });
console.log("ok");
