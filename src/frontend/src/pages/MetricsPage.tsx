import { useState, useEffect } from "react";
import { getAllModelMetrics } from "../api/mlModels";
import type { AllModelsMetrics } from "../types/mlModels";
import { formatMetric, formatDate, isProduction } from "../utils/metricsFormat";
import { ApiError } from "../types/api";
import { getUserFacingMessage } from "../utils/errorMessages";
import "./MetricsPage.css";

export default function MetricsPage() {
  const [data, setData] = useState<AllModelsMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAllModelMetrics()
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof ApiError) {
          setError(getUserFacingMessage(e));
        } else if (e instanceof Error) {
          setError(e.message);
        } else {
          setError(String(e));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="metrics-loading">Загрузка…</div>;
  }

  if (error) {
    return <div className="metrics-error">{error}</div>;
  }

  if (!data) {
    return null;
  }

  const entries = Object.entries(data.models);
  if (entries.length === 0) {
    return <div className="metrics-empty-state">Модели не найдены в registry</div>;
  }

  return (
    <div className="metrics-page">
      <h1>Метрики моделей</h1>
      {entries.map(([name, m]) => (
        <section key={name} className="model-section">
          <h2>{name}</h2>
          {m.versions.length === 0 ? (
            <p className="metrics-empty-versions">Нет версий</p>
          ) : (
            <div className="metrics-table-wrapper">
              <table className="metrics-table">
                <thead>
                  <tr>
                    <th>Версия</th>
                    <th>Alias</th>
                    <th>RMSE</th>
                    <th>MAE</th>
                    <th>R²</th>
                    <th>Дата</th>
                  </tr>
                </thead>
                <tbody>
                  {m.versions.map((v) => {
                    const rmse = v.metrics.rmse ?? v.metrics.test_rmse;
                    const mae = v.metrics.mae ?? v.metrics.test_mae;
                    const r2 = v.metrics.r2 ?? v.metrics.test_r2;

                    return (
                      <tr
                        key={v.version}
                        className={isProduction(v.aliases) ? "production" : ""}
                      >
                        <td>{v.version}</td>
                        <td>{v.aliases.length > 0 ? v.aliases.join(", ") : "—"}</td>
                        <td>{formatMetric(rmse)}</td>
                        <td>{formatMetric(mae)}</td>
                        <td>{formatMetric(r2)}</td>
                        <td>{formatDate(v.created_at)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
