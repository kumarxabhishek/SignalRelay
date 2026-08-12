import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("build contains the SignalRelay research dashboard", async () => {
  const page = await readFile(new URL("../app/page.tsx", import.meta.url), "utf8");
  const layout = await readFile(new URL("../app/layout.tsx", import.meta.url), "utf8");
  const css = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");

  assert.match(layout, /SignalRelay — Evidence-backed NSE market research/i);
  assert.match(page, /Inspect a stock/);
  assert.match(page, /Research only — not investment advice/);
  assert.match(page, /Evidence-checked signal analysis/);
  assert.match(page, /No records observed/);
  assert.match(page, /View complete machine-readable payload/);
  assert.match(page, /NSE stock suggestions/);
  assert.match(page, /aria-autocomplete="list"/);
  assert.match(css, /font-family: Inter/);
  assert.doesNotMatch(`${page}\n${layout}`, /codex-preview|Your site is taking shape|react-loading-skeleton/i);
});
