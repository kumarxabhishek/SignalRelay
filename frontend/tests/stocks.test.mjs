import assert from "node:assert/strict";
import test from "node:test";

import { findStockMatches, parseNseEquityCsv } from "../lib/stocks.ts";

const stocks = parseNseEquityCsv(`SYMBOL,NAME OF COMPANY, SERIES
RELIANCE,Reliance Industries Limited,EQ
RELAXO,Relaxo Footwears Limited,EQ
HDFCBANK,HDFC Bank Limited,EQ
HDFCLIFE,HDFC Life Insurance Company Limited,EQ`);

test("parses the official NSE equity directory columns", () => {
  assert.deepEqual(stocks[0], { symbol: "RELIANCE", name: "Reliance Industries Limited" });
});

test("ranks symbol matches before company-name matches", () => {
  assert.deepEqual(findStockMatches(stocks, "rel").map(({ symbol }) => symbol), ["RELAXO", "RELIANCE"]);
  assert.deepEqual(findStockMatches(stocks, "insurance").map(({ symbol }) => symbol), ["HDFCLIFE"]);
});

test("puts an exact ticker first and respects the result limit", () => {
  assert.equal(findStockMatches(stocks, "HDFCBANK", 1)[0]?.symbol, "HDFCBANK");
  assert.equal(findStockMatches(stocks, "HDFC", 1).length, 1);
});
