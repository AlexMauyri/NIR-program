import { useState, useEffect, useMemo } from "react";
import { StockChart } from "../components/StockChart";
import ModelSelector from "../components/ModelSelector";
import { getModels, getAllModelMetrics } from "../api/mlModels";
import type { ModelInfo } from "../api/mlModels";
import { usePredictions } from "../hooks/usePredictions";

export default function HomePage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const { predictions, isLoading, error: predictionsError } = usePredictions(selectedModel);

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
      {(modelsError ?? predictionsError) && (
        <div
          className="error"
          style={{
            color: "#dc2626",
            marginBottom: "12px",
            fontSize: "0.9rem",
          }}
        >
          {modelsError ?? predictionsError}
        </div>
      )}
      <StockChart ticker="SBER" predictions={chartPredictions} />
    </>
  );
}
