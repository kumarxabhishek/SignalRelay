export type StockEntry = { symbol: string; name: string };

export function parseNseEquityCsv(csv: string): StockEntry[] {
  return csv.trim().split(/\r?\n/).slice(1).map((line) => {
    const [symbol, name] = line.split(",");
    return { symbol: symbol?.trim() || "", name: name?.trim() || "" };
  }).filter((entry) => entry.symbol && entry.name);
}

export function findStockMatches(stocks: StockEntry[], input: string, limit = 7): StockEntry[] {
  const query = input.trim().toUpperCase();
  if (!query) return [];

  return stocks.map((stock) => {
    const symbol = stock.symbol.toUpperCase();
    const name = stock.name.toUpperCase();
    let rank = 5;
    if (symbol === query) rank = 0;
    else if (symbol.startsWith(query)) rank = 1;
    else if (name.startsWith(query)) rank = 2;
    else if (symbol.includes(query)) rank = 3;
    else if (name.includes(query)) rank = 4;
    return { stock, rank };
  }).filter(({ rank }) => rank < 5)
    .sort((left, right) => left.rank - right.rank || left.stock.symbol.localeCompare(right.stock.symbol))
    .slice(0, limit)
    .map(({ stock }) => stock);
}
