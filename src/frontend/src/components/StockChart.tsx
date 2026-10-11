import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TooltipContentProps } from 'recharts/types/component/Tooltip';
import { getStockHistory } from '../api';
import { useApi } from '../hooks/useApi';
import { getUserFacingMessage } from '../utils/errorMessages';
import {
  calculateBollingerBands,
  calculateEMA,
  calculateMACD,
  calculateRSI,
  calculateSMA,
} from '../utils/indicators';
import type { IndicatorSettings } from '../types/indicators';
import { DEFAULT_INDICATOR_SETTINGS } from '../types/indicators';
import type { StockPricePoint } from '../types/stocks';
import { ChartSkeleton } from './ChartSkeleton';
import { IndicatorSelector } from './IndicatorSelector';
import './StockChart.css';

interface StockChartProps {
  ticker?: string;
  predictions?: {
    dates: string[];
    values: number[];
    model_name?: string;
  } | null;
  onVisibleRangeChange?: (startDate: string, endDate: string) => void;
  isPredictionsLoading?: boolean;
  predictionsError?: string | null;
  onRetryPredictions?: () => void;
}

interface IndexRange {
  startIndex: number;
  endIndex: number;
}

/** Точка главного графика цены с примешанными значениями индикаторов. */
interface PriceChartPoint extends StockPricePoint {
  sma: number | null;
  ema: number | null;
  bbUpper: number | null;
  bbMiddle: number | null;
  bbLower: number | null;
  prediction?: number | null;
}

const DEFAULT_WINDOW_DAYS = 30;
const MIN_VISIBLE_POINTS = 5;
const ZOOM_STEP = 0.15;
const SYNC_ID = 'stock-chart-sync';
const LOADING_BADGE_DELAY_MS = 300;

function formatDateShort(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

function formatDateFull(isoDate: string): string {
  const d = new Date(isoDate);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
}

/** Индексы окна по умолчанию — последние DEFAULT_WINDOW_DAYS дней от конца массива. */
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

/** Ограничивает диапазон [start, end] границами [0, maxIndex], сохраняя его ширину. */
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

/** Возвращает true, только если flag остаётся true дольше delayMs. */
function useDelayedFlag(flag: boolean, delayMs: number): boolean {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!flag) {
      setVisible(false);
      return;
    }
    const t = setTimeout(() => setVisible(true), delayMs);
    return () => clearTimeout(t);
  }, [flag, delayMs]);
  return visible;
}

function ChartTooltip({ active, payload }: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const point = payload[0].payload as PriceChartPoint;

  const formatPrice = (value: number | null | undefined) =>
    value != null ? `${value.toFixed(2)} ₽` : '—';

  return (
    <div className="stock-chart__tooltip">
      <div className="stock-chart__tooltip-date">{formatDateFull(point.date)}</div>
      {point.close != null && (
        <>
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
        </>
      )}
      {point.sma != null && (
        <div className="stock-chart__tooltip-row">
          <span className="stock-chart__tooltip-label">SMA</span>
          <span className="stock-chart__tooltip-value">{formatPrice(point.sma)}</span>
        </div>
      )}
      {point.ema != null && (
        <div className="stock-chart__tooltip-row">
          <span className="stock-chart__tooltip-label">EMA</span>
          <span className="stock-chart__tooltip-value">{formatPrice(point.ema)}</span>
        </div>
      )}
      {point.prediction != null && (
        <div className="stock-chart__tooltip-row">
          <span className="stock-chart__tooltip-label">Прогноз</span>
          <span
            className="stock-chart__tooltip-value"
            style={{ color: '#ff9800', fontWeight: 600 }}
          >
            {formatPrice(point.prediction)}
          </span>
        </div>
      )}
    </div>
  );
}

function SimpleTooltip({ active, payload, label, formatter }: {
  active?: boolean;
  payload?: { name: string; value: number | null; color?: string }[];
  label?: string;
  formatter?: (value: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="stock-chart__tooltip">
      <div className="stock-chart__tooltip-date">{formatDateFull(label ?? '')}</div>
      {payload.map((entry) =>
        entry.value != null ? (
          <div className="stock-chart__tooltip-row" key={entry.name}>
            <span className="stock-chart__tooltip-label" style={{ color: entry.color }}>
              {entry.name}
            </span>
            <span className="stock-chart__tooltip-value">
              {formatter ? formatter(entry.value) : entry.value.toFixed(2)}
            </span>
          </div>
        ) : null,
      )}
    </div>
  );
}

export function StockChart({
  ticker = 'SBER',
  predictions,
  onVisibleRangeChange,
  isPredictionsLoading,
  predictionsError,
  onRetryPredictions,
}: StockChartProps) {
  const [range, setRange] = useState<IndexRange | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [indicatorSettings, setIndicatorSettings] = useState<IndicatorSettings>(
    DEFAULT_INDICATOR_SETTINGS,
  );

  const showLoadingBadge = useDelayedFlag(!!isPredictionsLoading, LOADING_BADGE_DELAY_MS);

  // containerEl — это DOM-узел, положенный в state. Нужен, чтобы useEffect'ы
  // с нативными обработчиками гарантированно срабатывали после появления
  // контейнера в DOM (при первом рендере компонент возвращает <ChartSkeleton />,
  // и containerRef.current === null в момент первого прохода useEffect).
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerEl, setContainerEl] = useState<HTMLDivElement | null>(null);

  const setContainerRef = useCallback((node: HTMLDivElement | null) => {
    containerRef.current = node;
    setContainerEl(node);
  }, []);

  const rangeRef = useRef<IndexRange | null>(null);
  const chronologicalRef = useRef<StockPricePoint[]>([]);
  const dragStartRef = useRef<{ clientX: number; range: IndexRange } | null>(null);
  /** Первая дата массива на момент последней инициализации — для компенсации сдвига индексов. */
  const prevFirstDateRef = useRef<string | null>(null);

  const fetchHistory = useCallback(() => getStockHistory({ ticker }), [ticker]);
  const { data, error, isLoading, execute } = useApi(fetchHistory);

  useEffect(() => {
    execute();
  }, [execute]);

  const points = data?.data ?? [];

  const chronological = useMemo(() => {
    const sortedPoints = [...points].sort((a, b) => (a.date < b.date ? -1 : 1));
    if (!predictions || predictions.dates.length === 0) {
      return sortedPoints;
    }

    const existingDates = new Set(sortedPoints.map((p) => p.date));
    const extraPoints: StockPricePoint[] = [];

    predictions.dates.forEach((d) => {
      if (!existingDates.has(d)) {
        extraPoints.push({
          date: d,
          open: null,
          high: null,
          low: null,
          close: null,
        });
      }
    });

    if (extraPoints.length === 0) {
      return sortedPoints;
    }

    return [...sortedPoints, ...extraPoints].sort((a, b) => (a.date < b.date ? -1 : 1));
  }, [points, predictions]);

  // Refs для нативных обработчиков.
  useEffect(() => {
    rangeRef.current = range;
  }, [range]);

  useEffect(() => {
    chronologicalRef.current = chronological;
  }, [chronological]);

  // Инициализация range при первой загрузке данных.
  // При подгрузке прогнозов (первая дата массива сдвинулась влево)
  // НЕ сбрасываем зум, а компенсируем сдвиг индексов.
  useEffect(() => {
    if (chronological.length === 0) return;
    const firstDate = chronological[0].date;

    if (prevFirstDateRef.current === null) {
      prevFirstDateRef.current = firstDate;
      setRange(defaultIndexRange(chronological));
      return;
    }
    if (firstDate === prevFirstDateRef.current) {
      return;
    }
    const oldIdx = chronological.findIndex((p) => p.date === prevFirstDateRef.current);
    if (oldIdx === -1) {
      prevFirstDateRef.current = firstDate;
      setRange(defaultIndexRange(chronological));
      return;
    }
    setRange((prev) =>
      prev
        ? { startIndex: prev.startIndex + oldIdx, endIndex: prev.endIndex + oldIdx }
        : prev,
    );
    prevFirstDateRef.current = firstDate;
  }, [chronological]);

  // Уведомляем родителя об изменении видимого диапазона.
  useEffect(() => {
    if (!onVisibleRangeChange || !range || chronological.length === 0) return;
    const first = chronological[range.startIndex];
    const last = chronological[range.endIndex];
    if (!first || !last) return;
    onVisibleRangeChange(first.date, last.date);
  }, [range, chronological, onVisibleRangeChange]);

  const handleResetZoom = () => {
    setRange({ startIndex: 0, endIndex: Math.max(chronological.length - 1, 0) });
  };

  // Зум колесом мыши, центрированный на позиции курсора.
  useEffect(() => {
    const container = containerEl;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      const currentRange = rangeRef.current;
      const data = chronologicalRef.current;
      const maxIndex = data.length - 1;
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
  }, [containerEl]);

  // Панорамирование ЛКМ.
  useEffect(() => {
    const container = containerEl;
    if (!container) return;

    const handleMouseMove = (e: MouseEvent) => {
      const drag = dragStartRef.current;
      const data = chronologicalRef.current;
      const maxIndex = data.length - 1;
      if (!drag || maxIndex <= 0) return;

      const rect = container.getBoundingClientRect();
      const dx = e.clientX - drag.clientX;
      const width = drag.range.endIndex - drag.range.startIndex;
      // Тащим вправо (dx > 0) — окно сдвигается к более ранним датам.
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
  }, [containerEl]);

  const smaFull = useMemo(
    () =>
      indicatorSettings.sma.enabled
        ? calculateSMA(chronological, indicatorSettings.sma.period)
        : null,
    [chronological, indicatorSettings.sma.enabled, indicatorSettings.sma.period],
  );

  const emaFull = useMemo(
    () =>
      indicatorSettings.ema.enabled
        ? calculateEMA(chronological, indicatorSettings.ema.period)
        : null,
    [chronological, indicatorSettings.ema.enabled, indicatorSettings.ema.period],
  );

  const bollingerFull = useMemo(
    () =>
      indicatorSettings.bollinger.enabled
        ? calculateBollingerBands(
            chronological,
            indicatorSettings.bollinger.period,
            indicatorSettings.bollinger.stdDevMultiplier,
          )
        : null,
    [
      chronological,
      indicatorSettings.bollinger.enabled,
      indicatorSettings.bollinger.period,
      indicatorSettings.bollinger.stdDevMultiplier,
    ],
  );

  const rsiFull = useMemo(
    () =>
      indicatorSettings.rsi.enabled
        ? calculateRSI(chronological, indicatorSettings.rsi.period)
        : null,
    [chronological, indicatorSettings.rsi.enabled, indicatorSettings.rsi.period],
  );

  const macdFull = useMemo(
    () =>
      indicatorSettings.macd.enabled
        ? calculateMACD(
            chronological,
            indicatorSettings.macd.fastPeriod,
            indicatorSettings.macd.slowPeriod,
            indicatorSettings.macd.signalPeriod,
          )
        : null,
    [
      chronological,
      indicatorSettings.macd.enabled,
      indicatorSettings.macd.fastPeriod,
      indicatorSettings.macd.slowPeriod,
      indicatorSettings.macd.signalPeriod,
    ],
  );

  const visible = useMemo(() => {
    if (!range) return chronological;
    return chronological.slice(range.startIndex, range.endIndex + 1);
  }, [chronological, range]);

  const priceChartData = useMemo((): PriceChartPoint[] => {
    const predMap = new Map<string, number>();
    const actualMap = new Map<string, StockPricePoint>();
    points.forEach((p) => actualMap.set(p.date, p));

    if (predictions && predictions.dates.length > 0) {
      predictions.dates.forEach((d, idx) => {
        predMap.set(d, predictions.values[idx]);
      });
    }

    if (!range) {
      return visible.map((p) => {
        const actual = actualMap.get(p.date);
        return {
          ...p,
          open: actual ? actual.open : null,
          high: actual ? actual.high : null,
          low: actual ? actual.low : null,
          close: actual ? actual.close : null,
          sma: null,
          ema: null,
          bbUpper: null,
          bbMiddle: null,
          bbLower: null,
          prediction: predMap.get(p.date) ?? null,
        };
      });
    }
    return visible.map((p, i) => {
      const idx = range.startIndex + i;
      const actual = actualMap.get(p.date);
      return {
        ...p,
        open: actual ? actual.open : null,
        high: actual ? actual.high : null,
        low: actual ? actual.low : null,
        close: actual ? actual.close : null,
        sma: smaFull && smaFull[idx] ? smaFull[idx].value : null,
        ema: emaFull && emaFull[idx] ? emaFull[idx].value : null,
        bbUpper: bollingerFull && bollingerFull[idx] ? bollingerFull[idx].upper : null,
        bbMiddle: bollingerFull && bollingerFull[idx] ? bollingerFull[idx].middle : null,
        bbLower: bollingerFull && bollingerFull[idx] ? bollingerFull[idx].lower : null,
        prediction: predMap.get(p.date) ?? null,
      };
    });
  }, [visible, range, smaFull, emaFull, bollingerFull, predictions, points]);

  const rsiChartData = useMemo(() => {
    if (!range || !rsiFull) return [];
    return visible.map((p, i) => ({
      date: p.date,
      rsi: rsiFull[range.startIndex + i]?.value ?? null,
    }));
  }, [visible, range, rsiFull]);

  const macdChartData = useMemo(() => {
    if (!range || !macdFull) return [];
    return visible.map((p, i) => {
      const idx = range.startIndex + i;
      const item = macdFull[idx];
      return {
        date: p.date,
        macd: item?.macd ?? null,
        signal: item?.signal ?? null,
        histogram: item?.histogram ?? null,
      };
    });
  }, [visible, range, macdFull]);

  const yDomain = useMemo((): [number, number] | undefined => {
    const values: number[] = [];
    priceChartData.forEach((p) => {
      if (p.close != null) values.push(p.close);
      if (p.bbUpper != null) values.push(p.bbUpper);
      if (p.bbLower != null) values.push(p.bbLower);
      if (p.prediction != null) values.push(p.prediction);
    });
    if (values.length === 0) return undefined;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.05 || max * 0.05 || 1;
    return [Math.floor(min - padding), Math.ceil(max + padding)];
  }, [priceChartData]);

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

      <IndicatorSelector settings={indicatorSettings} onChange={setIndicatorSettings} />

      <div
        ref={setContainerRef}
        className={
          'stock-chart__plot' + (isDragging ? ' stock-chart__plot--dragging' : '')
        }
      >
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={priceChartData}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
            syncId={SYNC_ID}
          >
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
            <Legend verticalAlign="top" height={36} iconType="plainline" />

            {indicatorSettings.bollinger.enabled && (
              <>
                <Line
                  type="monotone"
                  dataKey="bbUpper"
                  stroke="#94a3b8"
                  strokeWidth={1}
                  strokeDasharray="4 3"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                  name="BB верх"
                />
                <Line
                  type="monotone"
                  dataKey="bbLower"
                  stroke="#94a3b8"
                  strokeWidth={1}
                  strokeDasharray="4 3"
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                  name="BB низ"
                />
                <Line
                  type="monotone"
                  dataKey="bbMiddle"
                  stroke="#a855f7"
                  strokeWidth={1}
                  dot={false}
                  connectNulls
                  isAnimationActive={false}
                  name="BB середина"
                />
              </>
            )}

            <Line
              type="monotone"
              dataKey="close"
              stroke="#2563eb"
              strokeWidth={2}
              dot={false}
              connectNulls
              isAnimationActive={false}
              name="Факт"
            />

            {predictions && predictions.dates.length > 0 && (
              <Line
                type="monotone"
                dataKey="prediction"
                name={`Прогноз ${predictions.model_name ?? ''}`.trim()}
                stroke="#ff9800"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={{ r: 3, fill: '#ff9800', strokeWidth: 0 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}

            {indicatorSettings.sma.enabled && (
              <Line
                type="monotone"
                dataKey="sma"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
                name={`SMA(${indicatorSettings.sma.period})`}
              />
            )}

            {indicatorSettings.ema.enabled && (
              <Line
                type="monotone"
                dataKey="ema"
                stroke="#10b981"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
                name={`EMA(${indicatorSettings.ema.period})`}
              />
            )}
          </LineChart>
        </ResponsiveContainer>

        {showLoadingBadge && !predictionsError && (
          <div className="stock-chart__loading-badge">Загрузка прогнозов…</div>
        )}

        {predictionsError && (
          <div className="stock-chart__error-badge">
            <span>Ошибка загрузки</span>
            {onRetryPredictions && (
              <button type="button" onClick={onRetryPredictions}>
                Повторить
              </button>
            )}
          </div>
        )}
      </div>

      {indicatorSettings.rsi.enabled && (
        <div className="stock-chart__panel">
          <span className="stock-chart__panel-title">
            RSI({indicatorSettings.rsi.period})
          </span>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart
              data={rsiChartData}
              margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
              syncId={SYNC_ID}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                minTickGap={32}
                tick={{ fontSize: 11 }}
              />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} width={64} />
              <ReferenceLine y={70} stroke="#dc2626" strokeDasharray="3 3" />
              <ReferenceLine y={30} stroke="#16a34a" strokeDasharray="3 3" />
              <Tooltip content={<SimpleTooltip formatter={(v) => v.toFixed(1)} />} />
              <Line
                type="monotone"
                dataKey="rsi"
                stroke="#7c3aed"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
                name="RSI"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {indicatorSettings.macd.enabled && (
        <div className="stock-chart__panel">
          <span className="stock-chart__panel-title">
            MACD({indicatorSettings.macd.fastPeriod}/{indicatorSettings.macd.slowPeriod}/
            {indicatorSettings.macd.signalPeriod})
          </span>
          <ResponsiveContainer width="100%" height={160}>
            <ComposedChart
              data={macdChartData}
              margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
              syncId={SYNC_ID}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateShort}
                minTickGap={32}
                tick={{ fontSize: 11 }}
              />
              <YAxis tick={{ fontSize: 11 }} width={64} />
              <ReferenceLine y={0} stroke="#ccc" />
              <Tooltip content={<SimpleTooltip formatter={(v) => v.toFixed(3)} />} />
              <Bar dataKey="histogram" name="Гистограмма" isAnimationActive={false}>
                {macdChartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      entry.histogram != null && entry.histogram >= 0 ? '#16a34a' : '#dc2626'
                    }
                  />
                ))}
              </Bar>
              <Line
                type="monotone"
                dataKey="macd"
                stroke="#2563eb"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
                name="MACD"
              />
              <Line
                type="monotone"
                dataKey="signal"
                stroke="#f97316"
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
                name="Сигнальная"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}