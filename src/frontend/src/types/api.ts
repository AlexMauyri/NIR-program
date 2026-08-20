/**
 * Общие типы, связанные с сетевым слоем приложения.
 */

/**
 * Категория ошибки, нормализованная под нужды UI.
 * Реализовано как const-объект (а не enum), т.к. проект собирается
 * с erasableSyntaxOnly/isolatedModules — enum там запрещён.
 */
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

/** Тело ошибки, которое ожидается от backend (может отличаться — тогда fallback). */
export interface ApiErrorPayload {
  message?: string;
  code?: string;
  details?: unknown;
}

/** Унифицированная ошибка, которую бросает http-клиент. Ловится в UI единообразно. */
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
    // Восстановление прототипной цепочки при таргете ES5
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}
