export interface StockPricePoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
}

export interface StockHistoryResponse {
  ticker: string;
  count: number;
  offset: number;
  limit: number;
  data: StockPricePoint[];
}
