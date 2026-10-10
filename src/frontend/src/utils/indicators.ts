import type { StockPricePoint } from '../types/stocks';

/** Точка произвольного скалярного индикатора (SMA, EMA, RSI). */
export interface IndicatorSeriesPoint {
  date: string;
  value: number | null;
}

/** Точка MACD: сама линия MACD, сигнальная линия и гистограмма разницы между ними. */
export interface MACDPoint {
  date: string;
  macd: number | null;
  signal: number | null;
  histogram: number | null;
}

/** Точка полос Боллинджера: верхняя/средняя (SMA)/нижняя границы. */
export interface BollingerPoint {
  date: string;
  upper: number | null;
  middle: number | null;
  lower: number | null;
}

/** Простое скользящее среднее по произвольному числовому ряду (null пропускает окно). */
function smaFromSeries(values: (number | null)[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null);
      continue;
    }
    let sum = 0;
    let isWindowValid = true;
    for (let j = i - period + 1; j <= i; j++) {
      const v = values[j];
      if (v == null) {
        isWindowValid = false;
        break;
      }
      sum += v;
    }
    result.push(isWindowValid ? sum / period : null);
  }
  return result;
}

/**
 * Экспоненциальное скользящее среднее по произвольному числовому ряду.
 * Стартовое значение — простое среднее первых `period` элементов (стандартный подход).
 * На пропусках (null) сохраняет предыдущее значение EMA без обновления.
 */
function emaFromSeries(values: (number | null)[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const result: (number | null)[] = [];
  let prevEma: number | null = null;

  for (let i = 0; i < values.length; i++) {
    const v = values[i];

    if (v == null) {
      result.push(prevEma);
      continue;
    }

    if (prevEma == null) {
      if (i < period - 1) {
        result.push(null);
        continue;
      }
      let sum = 0;
      let isWindowValid = true;
      for (let j = i - period + 1; j <= i; j++) {
        const vv = values[j];
        if (vv == null) {
          isWindowValid = false;
          break;
        }
        sum += vv;
      }
      if (!isWindowValid) {
        result.push(null);
        continue;
      }
      prevEma = sum / period;
      result.push(prevEma);
      continue;
    }

    prevEma = v * k + prevEma * (1 - k);
    result.push(prevEma);
  }

  return result;
}

/** Простое скользящее среднее (SMA) цены закрытия с настраиваемым окном. */
export function calculateSMA(data: StockPricePoint[], period: number): IndicatorSeriesPoint[] {
  const closes = data.map((p) => p.close);
  const values = smaFromSeries(closes, period);
  return data.map((p, i) => ({ date: p.date, value: values[i] }));
}

/** Экспоненциальное скользящее среднее (EMA) цены закрытия с настраиваемым окном. */
export function calculateEMA(data: StockPricePoint[], period: number): IndicatorSeriesPoint[] {
  const closes = data.map((p) => p.close);
  const values = emaFromSeries(closes, period);
  return data.map((p, i) => ({ date: p.date, value: values[i] }));
}

/**
 * Индекс относительной силы (RSI) по методу Уайлдера.
 * Стартовое среднее прироста/падения — простое среднее за первые `period`
 * изменений цены, далее — сглаживание Уайлдера.
 */
export function calculateRSI(data: StockPricePoint[], period = 14): IndicatorSeriesPoint[] {
  const closes = data.map((p) => p.close);
  const result: IndicatorSeriesPoint[] = data.map((p) => ({ date: p.date, value: null }));

  const gains: number[] = [];
  const losses: number[] = [];

  for (let i = 1; i < closes.length; i++) {
    const prev = closes[i - 1];
    const curr = closes[i];
    if (prev == null || curr == null) {
      gains.push(0);
      losses.push(0);
      continue;
    }
    const change = curr - prev;
    gains.push(change > 0 ? change : 0);
    losses.push(change < 0 ? -change : 0);
  }

  let avgGain: number | null = null;
  let avgLoss: number | null = null;

  // gains[i] соответствует closes[i + 1] — индекс со сдвигом на 1.
  for (let i = 0; i < gains.length; i++) {
    const dataIndex = i + 1;

    if (avgGain == null || avgLoss == null) {
      if (i < period - 1) continue;
      let sumGain = 0;
      let sumLoss = 0;
      for (let j = i - period + 1; j <= i; j++) {
        sumGain += gains[j];
        sumLoss += losses[j];
      }
      avgGain = sumGain / period;
      avgLoss = sumLoss / period;
    } else {
      avgGain = (avgGain * (period - 1) + gains[i]) / period;
      avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    }

    const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
    result[dataIndex] = { date: data[dataIndex].date, value: rsi };
  }

  return result;
}

/**
 * MACD: разница EMA(fastPeriod) и EMA(slowPeriod) цены закрытия, сигнальная
 * линия — EMA(signalPeriod) от самой линии MACD, гистограмма — их разница.
 */
export function calculateMACD(
  data: StockPricePoint[],
  fastPeriod = 12,
  slowPeriod = 26,
  signalPeriod = 9,
): MACDPoint[] {
  const closes = data.map((p) => p.close);
  const fastEma = emaFromSeries(closes, fastPeriod);
  const slowEma = emaFromSeries(closes, slowPeriod);

  const macdLine: (number | null)[] = data.map((_, i) => {
    const f = fastEma[i];
    const s = slowEma[i];
    return f != null && s != null ? f - s : null;
  });

  const signalLine = emaFromSeries(macdLine, signalPeriod);

  return data.map((p, i) => {
    const macd = macdLine[i];
    const signal = signalLine[i];
    const histogram = macd != null && signal != null ? macd - signal : null;
    return { date: p.date, macd, signal, histogram };
  });
}

/**
 * Полосы Боллинджера: средняя линия — SMA(period), верхняя/нижняя —
 * среднее ± stdDevMultiplier стандартных отклонений цены закрытия за то же окно.
 */
export function calculateBollingerBands(
  data: StockPricePoint[],
  period = 20,
  stdDevMultiplier = 2,
): BollingerPoint[] {
  const closes = data.map((p) => p.close);
  const result: BollingerPoint[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push({ date: data[i].date, upper: null, middle: null, lower: null });
      continue;
    }

    let sum = 0;
    let isWindowValid = true;
    for (let j = i - period + 1; j <= i; j++) {
      const c = closes[j];
      if (c == null) {
        isWindowValid = false;
        break;
      }
      sum += c;
    }

    if (!isWindowValid) {
      result.push({ date: data[i].date, upper: null, middle: null, lower: null });
      continue;
    }

    const mean = sum / period;
    let variance = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const c = closes[j] as number;
      variance += (c - mean) ** 2;
    }
    variance /= period;
    const stdDev = Math.sqrt(variance);

    result.push({
      date: data[i].date,
      middle: mean,
      upper: mean + stdDevMultiplier * stdDev,
      lower: mean - stdDevMultiplier * stdDev,
    });
  }

  return result;
}
