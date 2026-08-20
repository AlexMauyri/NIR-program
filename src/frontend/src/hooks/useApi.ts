import { useCallback, useState } from 'react';
import { ApiError, ApiErrorType } from '../types/api';

interface UseApiState<T> {
  data: T | null;
  error: ApiError | null;
  isLoading: boolean;
}

export function useApi<T, Args extends unknown[]>(
  requestFn: (...args: Args) => Promise<T>,
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    error: null,
    isLoading: false,
  });

  const execute = useCallback(
    async (...args: Args): Promise<T | undefined> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      try {
        const data = await requestFn(...args);
        setState({ data, error: null, isLoading: false });
        return data;
      } catch (err) {
        const apiError =
          err instanceof ApiError
            ? err
            : new ApiError('Непредвиденная ошибка', ApiErrorType.UNKNOWN);

        if (apiError.type === ApiErrorType.CANCELLED) {
          setState((prev) => ({ ...prev, isLoading: false }));
          return undefined;
        }

        setState({ data: null, error: apiError, isLoading: false });
        return undefined;
      }
    },
    [requestFn],
  );

  return { ...state, execute };
}
