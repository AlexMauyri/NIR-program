import { useState, useEffect } from "react";
import { StockChart } from "../components/StockChart";
import ModelSelector from "../components/ModelSelector";
import { getModels, getAllModelMetrics } from "../api/mlModels";
import type { ModelInfo } from "../api/mlModels";
import { getPredictions } from "../api/predictions";
import type { PredictionResponse } from "../types/predictions";

export default function HomePage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
          setError(e instanceof Error ? e.message : String(e));
        }
      });
  }, []);

  useEffect(() => {
    if (!selectedModel) return;
    const end = new Date();
    end.setDate(end.getDate() + 7);
    const start = new Date();
    start.setDate(start.getDate() - 90);

    setLoading(true);
    setError(null);
    getPredictions({
      model_name: selectedModel,
      start_date: start.toISOString().slice(0, 10),
      end_date: end.toISOString().slice(0, 10),
    })
      .then(setPredictions)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [selectedModel]);

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
          disabled={loading}
        />
        {loading && <span>Загрузка…</span>}
      </div>
      {error && (
        <div
          className="error"
          style={{
            color: "#dc2626",
            marginBottom: "12px",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}
      <StockChart
        ticker="SBER"
        predictions={
          predictions
            ? {
                dates: predictions.dates,
                values: predictions.predictions,
                model_name: predictions.model_name,
              }
            : null
        }
      />
    </>
  );
}
