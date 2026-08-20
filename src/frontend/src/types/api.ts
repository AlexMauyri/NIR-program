export const ApiErrorType = {
  /** Ошибка валидации/некорректный запрос и т.п. (4xx) */
  CLIENT_ERROR: 'CLIENT_ERROR',
  /** Не авторизован (401) */
  UNAUTHORIZED: 'UNAUTHORIZED',
  /** Доступ запрещён (403) */
  FORBIDDEN: 'FORBIDDEN',
  /** Ресурс не найден (404) */
  NOT_FOUND: 'NOT_FOUND',
  /** Ошибка на стороне сервера (5xx) */
  SERVER_ERROR: 'SERVER_ERROR',
  /** Сеть недоступна, таймаут, DNS и т.п. */
  NETWORK_ERROR: 'NETWORK_ERROR',
  /** Запрос отменён (AbortController / axios cancel) */
  CANCELLED: 'CANCELLED',
  /** Прочие непредвиденные ошибки */
  UNKNOWN: 'UNKNOWN',
} as const;

export type ApiErrorType = (typeof ApiErrorType)[keyof typeof ApiErrorType];

export interface ApiErrorPayload {
  message?: string;
  code?: string;
  details?: unknown;
}

export class ApiError extends Error {
  public readonly type: ApiErrorType;
  public readonly status?: number;
  public readonly payload?: ApiErrorPayload;

  constructor(
    message: string,
    type: ApiErrorType,
    status?: number,
    payload?: ApiErrorPayload,
  ) {
    super(message);
    this.name = 'ApiError';
    this.type = type;
    this.status = status;
    this.payload = payload;

    Object.setPrototypeOf(this, ApiError.prototype);
  }
}
