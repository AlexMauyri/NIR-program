import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TooltipContentProps } from 'recharts/types/component/Tooltip';
import { getStockHistory } from '../api';
import { useApi } from '../hooks/useApi';
import { getUserFacingMessage } from '../utils/errorMessages';
import { filterByPeriod } from '../utils/chartPeriod';
import type { ChartPeriod } from '../utils/chartPeriod';
import type { StockPricePoint } from '../types/stocks';
import { ChartSkeleton } from './ChartSkeleton';
import './StockChart.css';

interface StockChartProps {
  ticker?: string;
}

const PERIOD_OPTIONS: { value: ChartPeriod; label: string }[] = [
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
  { value: 'year', label: 'Год' },
  { value: 'all', label: 'Всё' },
];

function formatDateShort(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

function formatDateFull(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
}

function ChartTooltip({ active, payload }: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const point = payload[0].payload as StockPricePoint;

  const formatPrice = (value: number | null) =>
    value != null ? `${value.toFixed(2)} ₽` : '—';

  return (
    <div className="stock-chart__tooltip">
      <div className="stock-chart__tooltip-date">{formatDateFull(point.date)}</div>
      <div className="stock-chart__tooltip-row">
        <span className="stock-chart__tooltip-label">Открытие</span>
        <span className="stock-chart__tooltip-value">{formatPrice(point.open)}</span>
      </div>
      <div className="stock-chart__tooltip-row">
        <span className="stock-chart__tooltip-label">Закрытие</span>
        <span className="stock-chart__tooltip-value">
          {formatPrice(point.close)}
        </span>
      </div>
      <div className="stock-chart__tooltip-row">
        <span className="stock-chart__tooltip-label">Максимум</span>
        <span className="stock-chart__tooltip-value">{formatPrice(point.high)}</span>
      </div>
      <div className="stock-chart__tooltip-row">
        <span className="stock-chart__tooltip-label">Минимум</span>
        <span className="stock-chart__tooltip-value">{formatPrice(point.low)}</span>
      </div>
    </div>
  );
}

/** График исторических цен закрытия с переключением периода без повторных запросов. */
export function StockChart({ ticker = 'SBER' }: StockChartProps) {
  const [period, setPeriod] = useState<ChartPeriod>('month');

  const fetchHistory = useCallback(() => getStockHistory({ ticker }), [ticker]);
  const { data, error, isLoading, execute } = useApi(fetchHistory);

  useEffect(() => {
    execute();
  }, [execute]);

  const points = data?.data ?? [];

  // Данные приходят от новых к старым (order_by desc) — для графика нужен
  // хронологический порядок, разворачиваем один раз здесь.
  const chronological = useMemo(
    () => [...points].sort((a, b) => (a.date < b.date ? -1 : 1)),
    [points],
  );

  const filtered = useMemo(
    () => filterByPeriod(chronological, period),
    [chronological, period],
  );

  const yDomain = useMemo((): [number, number] | undefined => {
    const closes = filtered
      .map((p) => p.close)
      .filter((v): v is number => v != null);
    if (closes.length === 0) return undefined;
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const padding = (max - min) * 0.05 || max * 0.05 || 1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [filtered]);

  if (isLoading && points.length === 0) {
    return <ChartSkeleton />;
  }

  if (error) {
    return (
      <div className="stock-chart__error" role="alert">
        {getUserFacingMessage(error)}
      </div>
    );
  }

  if (filtered.length === 0) {
    return <div className="stock-chart__empty">Нет данных для отображения</div>;
  }

  return (
    <div className="stock-chart">
      <div className="stock-chart__header">
        <h2 className="stock-chart__title">{ticker}: цена закрытия</h2>
        <div className="stock-chart__periods">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              className={
                'stock-chart__period-btn' +
                (period === opt.value ? ' stock-chart__period-btn--active' : '')
              }
              onClick={() => setPeriod(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={filtered} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateShort}
            minTickGap={32}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={yDomain ?? ['auto', 'auto']}
            tick={{ fontSize: 12 }}
            width={64}
          />
          <Tooltip content={<ChartTooltip />} />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
