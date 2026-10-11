import { useCallback, useEffect, useRef, useState } from "react";
import { getPredictions } from "../api/predictions";
import type { PredictionResponse } from "../types/predictions";

export interface DateRange {
  start: string;
  end: string;
}

interface UsePredictionsResult {
  predictions: PredictionResponse | null;
  isLoading: boolean;
  error: string | null;
  minLoadedDate: string | null;
  loadRange: (startDate: string, endDate: string) => Promise<void>;
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function shiftDay(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function mergeIntervals(intervals: DateRange[]): DateRange[] {
  const sorted = [...intervals].sort((a, b) => (a.start < b.start ? -1 : a.start > b.start ? 1 : 0));
  const result: DateRange[] = [];
  for (const interval of sorted) {
    const last = result[result.length - 1];
    if (last && interval.start <= shiftDay(last.end, 1)) {
      if (interval.end > last.end) last.end = interval.end;
    } else {
      result.push({ ...interval });
    }
  }
  return result;
}

function subtractIntervals(target: DateRange, covered: DateRange[]): DateRange[] {
  const gaps: DateRange[] = [];
  let cursor = target.start;
  for (const c of covered) {
    if (c.end < cursor) continue;
    if (c.start > target.end) break;
    if (c.start > cursor) gaps.push({ start: cursor, end: shiftDay(c.start, -1) });
    cursor = shiftDay(c.end, 1);
    if (cursor > target.end) return gaps;
  }
  if (cursor <= target.end) gaps.push({ start: cursor, end: target.end });
  return gaps;
}

function buildResponse(model: string, byDate: Map<string, number>): PredictionResponse | null {
  if (byDate.size === 0) return null;
  const entries = [...byDate.entries()].sort(([a], [b]) => (a < b ? -1 : 1));
  return {
    model_name: model,
    dates: entries.map(([date]) => date),
    predictions: entries.map(([, value]) => value),
  };
}

export function usePredictions(selectedModel: string | null): UsePredictionsResult {
  const [predictions, setPredictions] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [minLoadedDate, setMinLoadedDate] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const loadedRef = useRef<DateRange[]>([]);
  const byDateRef = useRef<Map<string, number>>(new Map());
  const exhaustedBeforeRef = useRef<string | null>(null);
  const inFlightRef = useRef<Set<string>>(new Set());

  const fetchRange = useCallback(
    (startDate: string, endDate: string, signal?: AbortSignal): Promise<PredictionResponse> => {
      if (!selectedModel) return Promise.reject(new Error("model not selected"));
      return getPredictions(
        { model_name: selectedModel, start_date: startDate, end_date: endDate },
        signal,
      );
    },
    [selectedModel],
  );

  const loadRange = useCallback(
    async (startDate: string, endDate: string): Promise<void> => {
      const controller = abortRef.current;
      if (!selectedModel || !controller || controller.signal.aborted) return;

      let from = startDate;
      const exhaustedBefore = exhaustedBeforeRef.current;
      if (exhaustedBefore) {
        if (endDate < exhaustedBefore) return;
        if (from < exhaustedBefore) from = exhaustedBefore;
      }

      const holes = subtractIntervals({ start: from, end: endDate }, loadedRef.current);
      try {
        for (const hole of holes) {
          const key = `${hole.start}|${hole.end}`;
          if (inFlightRef.current.has(key)) continue;
          inFlightRef.current.add(key);
          setIsLoading(true);
          setError(null);
          try {
            const data = await fetchRange(hole.start, hole.end, controller.signal);
            if (controller.signal.aborted) return;

            loadedRef.current = mergeIntervals([...loadedRef.current, hole]);
            data.dates.forEach((date, i) => byDateRef.current.set(date, data.predictions[i]));
            if (data.predictions.length === 0) {
              const candidate = shiftDay(hole.end, 1);
              if (!exhaustedBeforeRef.current || candidate > exhaustedBeforeRef.current) {
                exhaustedBeforeRef.current = candidate;
              }
            }
            setPredictions(buildResponse(selectedModel, byDateRef.current));
            if (data.dates.length > 0) {
              const earliest = data.dates.reduce((a, b) => (b < a ? b : a));
              setMinLoadedDate((prev) => (prev && prev < earliest ? prev : earliest));
            }
          } catch (e) {
            if (controller.signal.aborted) return;
            setError(e instanceof Error ? e.message : String(e));
            return;
          } finally {
            if (!controller.signal.aborted) inFlightRef.current.delete(key);
          }
        }
      } finally {
        if (!controller.signal.aborted && inFlightRef.current.size === 0) setIsLoading(false);
      }
    },
    [selectedModel, fetchRange],
  );

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    loadedRef.current = [];
    byDateRef.current = new Map();
    exhaustedBeforeRef.current = null;
    inFlightRef.current = new Set();

    setPredictions(null);
    setError(null);
    setIsLoading(false);
    setMinLoadedDate(null);
    if (!selectedModel) return;

    const end = new Date();
    end.setDate(end.getDate() + 7);
    const start = new Date();
    start.setDate(start.getDate() - 90);
    void loadRange(toIsoDate(start), toIsoDate(end));

    return () => controller.abort();
  }, [selectedModel, loadRange]);

  return { predictions, isLoading, error, minLoadedDate, loadRange };
}
