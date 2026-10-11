import { useCallback, useEffect, useState } from "react";
import { getPredictions } from "../api/predictions";
import type { PredictionResponse } from "../types/predictions";

interface UsePredictionsResult {
  predictions: PredictionResponse | null;
  isLoading: boolean;
  error: string | null;
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function usePredictions(selectedModel: string | null): UsePredictionsResult {
  const [predictions, setPredictions] = useState<PredictionResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRange = useCallback(
    async (startDate: string, endDate: string): Promise<PredictionResponse | null> => {
      if (!selectedModel) return null;
      const data = await getPredictions({
        model_name: selectedModel,
        start_date: startDate,
        end_date: endDate,
      });
      return data.predictions.length > 0 ? data : null;
    },
    [selectedModel],
  );

  useEffect(() => {
    setPredictions(null);
    setError(null);
    setIsLoading(false);
    if (!selectedModel) return;

    let cancelled = false;
    const end = new Date();
    end.setDate(end.getDate() + 7);
    const start = new Date();
    start.setDate(start.getDate() - 90);

    setIsLoading(true);
    fetchRange(toIsoDate(start), toIsoDate(end))
      .then((data) => {
        if (!cancelled) setPredictions(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedModel, fetchRange]);

  return { predictions, isLoading, error };
}
