import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { StockChart } from "../components/StockChart";
import ModelSelector from "../components/ModelSelector";
import { getModels, getAllModelMetrics } from "../api/mlModels";
import type { ModelInfo } from "../api/mlModels";
import { usePredictions } from "../hooks/usePredictions";

const BATCH_DAYS = 90;
const PREFETCH_THRESHOLD_DAYS = 15;
const DAY_MS = 86_400_000;

function shiftIsoDate(isoDate: string, days: number): string {
  const time = new Date(`${isoDate}T00:00:00Z`).getTime();
  return new Date(time + days * DAY_MS).toISOString().slice(0, 10);
}

function daysBetween(from: string, to: string): number {
  const diff = new Date(`${to}T00:00:00Z`).getTime() - new Date(`${from}T00:00:00Z`).getTime();
  return Math.round(diff / DAY_MS);
}

export default function HomePage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const {
    predictions,
    isLoading,
    error: predictionsError,
    minLoadedDate,
    loadRange,
  } = usePredictions(selectedModel);

  // Последний запрошенный батч — для кнопки "Повторить" при ошибке.
  const lastBatchRef = useRef<{ start: string; end: string } | null>(null);

  const chartPredictions = useMemo(
    () =>
      predictions
        ? {
            dates: predictions.dates,
            values: predictions.predictions,
            model_name: predictions.model_name,
          }
        : null,
    [predictions],
  );

  // Фоновая подгрузка — это когда прогнозы уже есть, но грузится ещё батч.
  // Плашку в StockChart показываем только для неё (первичная загрузка — скелетон).
  const isBackgroundLoad = isLoading && !!predictions;

  const handleVisibleRangeChange = useCallback(
    (startDate: string) => {
      if (!selectedModel || !minLoadedDate) return;
      if (startDate >= minLoadedDate) return;
      if (daysBetween(startDate, minLoadedDate) > PREFETCH_THRESHOLD_DAYS) return;

      const nextEnd = shiftIsoDate(minLoadedDate, -1);
      const nextStart = shiftIsoDate(nextEnd, -(BATCH_DAYS - 1));
      lastBatchRef.current = { start: nextStart, end: nextEnd };
      void loadRange(nextStart, nextEnd);
    },
    [selectedModel, minLoadedDate, loadRange],
  );

  const handleRetryPredictions = useCallback(() => {
    const b = lastBatchRef.current;
    if (!b) return;
    void loadRange(b.start, b.end);
  }, [loadRange]);

  useEffect(() => {
    getModels()
      .then(async (fetchedModels) => {
        if (fetchedModels && fetchedModels.length > 0) {
          setModels(fetchedModels);
        } else {
          // Если /ml-models вернул пустой список, пробуем взять имена из /ml-models/metrics
          try {
            const metricsData = await getAllModelMetrics();
            const fallbackModels: ModelInfo[] = Object.keys(metricsData.models).map((name) => ({
              name,
              version: "",
              alias: "production",
              metrics: {},
            }));
            setModels(fallbackModels);
          } catch {
            setModels([]);
          }
        }
      })
      .catch(async (e) => {
        try {
          const metricsData = await getAllModelMetrics();
          const fallbackModels: ModelInfo[] = Object.keys(metricsData.models).map((name) => ({
            name,
            version: "",
            alias: "production",
            metrics: {},
          }));
          setModels(fallbackModels);
        } catch {
          setModelsError(e instanceof Error ? e.message : String(e));
        }
      });
  }, []);

  return (
    <>
      <div
        className="home-controls"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "16px",
          flexWrap: "wrap",
        }}
      >
        <ModelSelector
          models={models}
          selected={selectedModel}
          onChange={setSelectedModel}
          disabled={isLoading}
        />
        {isLoading && <span>Загрузка…</span>}
      </div>
      {modelsError && (
        <div
          className="error"
          style={{
            color: "#dc2626",
            marginBottom: "12px",
            fontSize: "0.9rem",
          }}
        >
          {modelsError}
        </div>
      )}
      <StockChart
        ticker="SBER"
        predictions={chartPredictions}
        onVisibleRangeChange={handleVisibleRangeChange}
        isPredictionsLoading={isBackgroundLoad}
        predictionsError={predictionsError}
        onRetryPredictions={handleRetryPredictions}
      />
    </>
  );
}