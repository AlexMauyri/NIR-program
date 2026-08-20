import { get } from './httpClient';
import type { StockHistoryResponse } from '../types/stocks';

interface GetStockHistoryParams {
  ticker?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}

/**
 * Загружает историю цен по тикеру. По умолчанию берёт максимум записей
 * (10000, лимит backend), т.к. фильтрация по периоду на клиенте (см.
 * StockChart) выполняется уже над загруженным массивом — без повторных
 * запросов при переключении периода.
 */
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
