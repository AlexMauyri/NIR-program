import { useCallback, useEffect } from 'react';
import { get } from '../api';
import { useApi } from '../hooks/useApi';
import { getUserFacingMessage } from '../utils/errorMessages';

interface HealthResponse {
  status: string;
}

/**
 * Демонстрационный компонент: проверяет доступность backend через /health.
 * Служит примером использования http-клиента и useApi в остальных фичах.
 */
export function HealthStatus() {
  const fetchHealth = useCallback(() => get<HealthResponse>('/health'), []);
  const { data, error, isLoading, execute } = useApi(fetchHealth);

  useEffect(() => {
    execute();
  }, [execute]);

  if (isLoading) {
    return <p>Проверка соединения с сервером…</p>;
  }

  if (error) {
    return <p role="alert">{getUserFacingMessage(error)}</p>;
  }

  return <p>Статус backend: {data?.status ?? 'неизвестен'}</p>;
}
