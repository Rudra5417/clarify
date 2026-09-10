import { cardHtml } from "../web/card.mjs";

const html = cardHtml({
  type: "bill",
  sender: "City Water",
  action: "Pay 84.12",
  summary: "You owe 84.12 by Sep 21.",
  warnings: ["overdue"],
  page_limit_hit: true,
  fields: [
    {
      key: "deadline",
      label: "Deadline",
      value: "2026-09-21",
      status: "unsure",
      reason: "two due dates",
    },
  ],
});

if (html.includes("<textarea")) throw new Error("chat box is forbidden");
if (!html.includes("unsure")) throw new Error("unsure not marked");
if (!html.includes("Pay 84.12")) throw new Error("action missing");
if (!html.includes("first 2 pages") && !html.includes("page")) {
  throw new Error("page limit warning missing");
}
console.log("ok");
