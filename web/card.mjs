function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** @param {object} card */
export function cardHtml(card) {
  const type = escapeHtml(card.type ?? "other");
  const sender = card.sender ? escapeHtml(card.sender) : "";
  const subject = card.subject ? escapeHtml(card.subject) : "";
  const what =
    sender || subject
      ? `${type} · ${sender || subject}`
      : type;

  const summary = escapeHtml(card.summary ?? "");
  const action = escapeHtml(card.action ?? "");

  const warnings = Array.isArray(card.warnings) ? card.warnings : [];
  let warningsBlock = "";
  if (warnings.length > 0) {
    const items = warnings
      .map((w) => `<li>${escapeHtml(w)}</li>`)
      .join("");
    warningsBlock = `<section class="warnings"><h2>Warnings</h2><ul>${items}</ul></section>`;
  }

  let pageLimitBlock = "";
  if (card.page_limit_hit) {
    pageLimitBlock =
      `<section class="page-limit" role="status">I only read the first 2 pages</section>`;
  }

  const fields = Array.isArray(card.fields) ? card.fields : [];
  const fieldsHtml = fields
    .map((f) => {
      const unsure = f.status === "unsure";
      const cls = unsure ? "field unsure" : "field sure";
      const label = escapeHtml(f.label ?? f.key ?? "");
      const value = escapeHtml(f.value ?? "");
      const reason =
        unsure && f.reason
          ? `<span class="reason">${escapeHtml(f.reason)}</span>`
          : "";
      const status = escapeHtml(f.status ?? "unsure");
      return (
        `<div class="${cls}" data-key="${escapeHtml(f.key ?? "")}">` +
        `<span class="label">${label}</span>` +
        `<input class="value" type="text" value="${value}" />` +
        `<span class="status">${status}</span>` +
        reason +
        `</div>`
      );
    })
    .join("");

  return (
    `<article class="card">` +
    `<header class="what-this-is">${what}</header>` +
    `<section class="summary"><h2>In plain language</h2><p>${summary}</p></section>` +
    `<section class="action"><h2>Do this</h2><p class="action-text">${action}</p></section>` +
    warningsBlock +
    pageLimitBlock +
    `<section class="fields"><h2>Fields</h2>${fieldsHtml}</section>` +
    `</article>`
  );
}

/** @param {HTMLElement} el @param {object} card */
export function renderCard(el, card) {
  el.innerHTML = cardHtml(card);
}
