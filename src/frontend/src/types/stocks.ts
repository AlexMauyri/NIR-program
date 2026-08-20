/** Одна запись цены за день, как её отдаёт backend (GET /stocks/history). */
export interface StockPricePoint {
  date: string; // ISO-строка YYYY-MM-DD
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
}

/** Ответ GET /stocks/history. */
export interface StockHistoryResponse {
  ticker: string;
  count: number;
  offset: number;
  limit: number;
  data: StockPricePoint[];
}
