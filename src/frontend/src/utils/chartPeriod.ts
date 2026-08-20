import type { StockPricePoint } from '../types/stocks';

export type ChartPeriod = 'week' | 'month' | 'year' | 'all';

const PERIOD_DAYS: Record<Exclude<ChartPeriod, 'all'>, number> = {
  week: 7,
  month: 30,
  year: 365,
};

/**
 * Фильтрует уже загруженные точки по периоду относительно самой свежей
 * даты в наборе данных (а не относительно "сегодня" — данные могут быть
 * не самыми последними). Для 'all' возвращает данные как есть.
 */
export function filterByPeriod(
  data: StockPricePoint[],
  period: ChartPeriod,
): StockPricePoint[] {
  if (period === 'all' || data.length === 0) {
    return data;
  }

  const latestDate = data.reduce(
    (max, point) => (point.date > max ? point.date : max),
    data[0].date,
  );

  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - PERIOD_DAYS[period]);
  const cutoffISO = cutoff.toISOString().slice(0, 10);

  return data.filter((point) => point.date >= cutoffISO);
}
