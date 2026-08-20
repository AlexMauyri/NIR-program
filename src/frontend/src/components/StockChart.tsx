import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import type { StockPricePoint } from '../types/stocks';
import { ChartSkeleton } from './ChartSkeleton';
import './StockChart.css';

interface StockChartProps {
  ticker?: string;
}

interface IndexRange {
  startIndex: number;
  endIndex: number;
}

const DEFAULT_WINDOW_DAYS = 30;
const MIN_VISIBLE_POINTS = 5;
const ZOOM_STEP = 0.15;

function formatDateShort(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

function formatDateFull(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
}

function defaultIndexRange(data: StockPricePoint[]): IndexRange {
  const lastIndex = data.length - 1;
  if (data.length === 0) {
    return { startIndex: 0, endIndex: 0 };
  }

  const latestDate = data[lastIndex].date;
  const cutoff = new Date(latestDate);
  cutoff.setDate(cutoff.getDate() - DEFAULT_WINDOW_DAYS);
  const cutoffISO = cutoff.toISOString().slice(0, 10);

  const startIndex = data.findIndex((p) => p.date >= cutoffISO);
  return {
    startIndex: startIndex === -1 ? 0 : startIndex,
    endIndex: lastIndex,
  };
}

function clampRange(startIndex: number, endIndex: number, maxIndex: number): IndexRange {
  let start = startIndex;
  let end = endIndex;
  if (start < 0) {
    end -= start;
    start = 0;
  }
  if (end > maxIndex) {
    start -= end - maxIndex;
    end = maxIndex;
  }
  start = Math.max(0, Math.round(start));
  end = Math.min(maxIndex, Math.round(end));
  return { startIndex: start, endIndex: end };
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
        <span className="stock-chart__tooltip-value stock-chart__tooltip-value--close">
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

export function StockChart({ ticker = 'SBER' }: StockChartProps) {
  const [range, setRange] = useState<IndexRange | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const rangeRef = useRef<IndexRange | null>(null);
  const dragStartRef = useRef<{ clientX: number; range: IndexRange } | null>(null);

  const fetchHistory = useCallback(() => getStockHistory({ ticker }), [ticker]);
  const { data, error, isLoading, execute } = useApi(fetchHistory);

  useEffect(() => {
    execute();
  }, [execute]);

  const points = data?.data ?? [];

  const chronological = useMemo(
    () => [...points].sort((a, b) => (a.date < b.date ? -1 : 1)),
    [points],
  );

  useEffect(() => {
    if (chronological.length > 0) {
      setRange(defaultIndexRange(chronological));
    }
  }, [chronological.length, ticker]);

  useEffect(() => {
    rangeRef.current = range;
  }, [range]);

  const handleResetZoom = () => {
    setRange({ startIndex: 0, endIndex: Math.max(chronological.length - 1, 0) });
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      const currentRange = rangeRef.current;
      const maxIndex = chronological.length - 1;
      if (!currentRange || maxIndex <= 0) return;

      e.preventDefault();

      const rect = container.getBoundingClientRect();
      const fraction = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));

      const { startIndex, endIndex } = currentRange;
      const width = endIndex - startIndex;
      const anchorIndex = startIndex + fraction * width;

      const zoomFactor = e.deltaY < 0 ? 1 - ZOOM_STEP : 1 + ZOOM_STEP;
      const newWidth = Math.min(
        maxIndex,
        Math.max(MIN_VISIBLE_POINTS, width * zoomFactor),
      );

      const newStart = anchorIndex - fraction * newWidth;
      const newEnd = newStart + newWidth;

      setRange(clampRange(newStart, newEnd, maxIndex));
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [chronological.length]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const drag = dragStartRef.current;
      const maxIndex = chronological.length - 1;
      if (!drag || maxIndex <= 0) return;

      const rect = container.getBoundingClientRect();
      const dx = e.clientX - drag.clientX;
      const width = drag.range.endIndex - drag.range.startIndex;
      const indexDelta = -(dx / rect.width) * width;

      setRange(
        clampRange(
          drag.range.startIndex + indexDelta,
          drag.range.endIndex + indexDelta,
          maxIndex,
        ),
      );
    };

    const handleMouseUp = () => {
      dragStartRef.current = null;
      setIsDragging(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    const handleMouseDown = (e: MouseEvent) => {
      const currentRange = rangeRef.current;
      if (e.button !== 0 || !currentRange) return;
      dragStartRef.current = { clientX: e.clientX, range: currentRange };
      setIsDragging(true);
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    };

    container.addEventListener('mousedown', handleMouseDown);
    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [chronological.length]);

  const visible = useMemo(() => {
    if (!range) return chronological;
    return chronological.slice(range.startIndex, range.endIndex + 1);
  }, [chronological, range]);

  const yDomain = useMemo((): [number, number] | undefined => {
    const closes = visible.map((p) => p.close).filter((v): v is number => v != null);
    if (closes.length === 0) return undefined;
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const padding = (max - min) * 0.05 || max * 0.05 || 1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [visible]);

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

  if (chronological.length === 0) {
    return <div className="stock-chart__empty">Нет данных для отображения</div>;
  }

  const isZoomedOrPanned =
    range != null && (range.startIndex !== 0 || range.endIndex !== chronological.length - 1);

  return (
    <div className="stock-chart">
      <div className="stock-chart__header">
        <h2 className="stock-chart__title">{ticker}: цена закрытия</h2>
        {isZoomedOrPanned && (
          <button
            type="button"
            className="stock-chart__reset-btn"
            onClick={handleResetZoom}
          >
            Сбросить зум
          </button>
        )}
      </div>

      <div
        ref={containerRef}
        className={
          'stock-chart__plot' + (isDragging ? ' stock-chart__plot--dragging' : '')
        }
      >
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={visible} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
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
    </div>
  );
}
