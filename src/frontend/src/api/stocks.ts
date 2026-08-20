import { get } from './httpClient';
import type { StockHistoryResponse } from '../types/stocks';

interface GetStockHistoryParams {
  ticker?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}

export function getStockHistory(
  params: GetStockHistoryParams = {},
): Promise<StockHistoryResponse> {
  const { ticker = 'SBER', dateFrom, dateTo, limit = 10000, offset = 0 } = params;

  return get<StockHistoryResponse>('/stocks/history', {
    params: {
      ticker,
      date_from: dateFrom,
      date_to: dateTo,
      limit,
      offset,
    },
  });
}
