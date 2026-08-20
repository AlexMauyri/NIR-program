import axios from 'axios';
import type {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from 'axios';
import { ApiError, ApiErrorType } from '../types/api';
import type { ApiErrorPayload } from '../types/api';

/**
 * Базовый URL backend. Обязателен — при отсутствии переменной окружения
 * приложение падает на старте, а не молча стучится в '/'.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!BASE_URL) {
  // eslint-disable-next-line no-console
  console.error(
    '[httpClient] VITE_API_BASE_URL не задан. Проверьте .env / .env.production.',
  );
}

const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS) || 15_000;

/** Единственный экземпляр axios, используемый всем приложением. */
export const httpClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: DEFAULT_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Точка расширения для авторизации: подставляет токен из хранилища,
 * если он есть. Хранилище токена намеренно не реализовано здесь —
 * подключается модуль аутентификации при необходимости.
 */
httpClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(error),
);

/** Преобразует любую ошибку axios/сети в единый ApiError. */
function normalizeError(error: AxiosError<ApiErrorPayload>): ApiError {
  // Запрос отменён (например, размонтирование компонента)
  if (axios.isCancel(error)) {
    return new ApiError('Запрос отменён', ApiErrorType.CANCELLED);
  }

  // Нет ответа от сервера: обрыв сети, DNS, таймаут, CORS-блокировка и т.п.
  if (!error.response) {
    const isTimeout = error.code === 'ECONNABORTED';
    return new ApiError(
      isTimeout
        ? 'Превышено время ожидания ответа от сервера'
        : 'Сервер недоступен. Проверьте подключение к сети',
      ApiErrorType.NETWORK_ERROR,
    );
  }

  const { status, data } = error.response;
  const payload: ApiErrorPayload | undefined =
    data && typeof data === 'object' ? data : undefined;
  const serverMessage = payload?.message;

  if (status === 401) {
    return new ApiError(
      serverMessage ?? 'Требуется авторизация',
      ApiErrorType.UNAUTHORIZED,
      status,
      payload,
    );
  }
  if (status === 403) {
    return new ApiError(
      serverMessage ?? 'Доступ запрещён',
      ApiErrorType.FORBIDDEN,
      status,
      payload,
    );
  }
  if (status === 404) {
    return new ApiError(
      serverMessage ?? 'Ресурс не найден',
      ApiErrorType.NOT_FOUND,
      status,
      payload,
    );
  }
  if (status >= 400 && status < 500) {
    return new ApiError(
      serverMessage ?? 'Некорректный запрос',
      ApiErrorType.CLIENT_ERROR,
      status,
      payload,
    );
  }
  if (status >= 500) {
    return new ApiError(
      serverMessage ?? 'Внутренняя ошибка сервера',
      ApiErrorType.SERVER_ERROR,
      status,
      payload,
    );
  }

  return new ApiError(
    serverMessage ?? 'Неизвестная ошибка',
    ApiErrorType.UNKNOWN,
    status,
    payload,
  );
}

httpClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorPayload>) => Promise.reject(normalizeError(error)),
);

/**
 * Обёртки над стандартными методами axios, чтобы вызывающий код нигде
 * напрямую не импортировал axios и работал только с ApiError.
 */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await httpClient.get<T>(url, config);
  return response.data;
}

export async function post<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await httpClient.post<T>(url, body, config);
  return response.data;
}

export async function put<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await httpClient.put<T>(url, body, config);
  return response.data;
}

export async function patch<T>(
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await httpClient.patch<T>(url, body, config);
  return response.data;
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await httpClient.delete<T>(url, config);
  return response.data;
}
