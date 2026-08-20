import { ApiError, ApiErrorType } from '../types/api';

const FALLBACK_MESSAGES: Record<ApiErrorType, string> = {
  [ApiErrorType.CLIENT_ERROR]: 'Некорректный запрос. Проверьте введённые данные',
  [ApiErrorType.UNAUTHORIZED]: 'Необходимо войти в систему',
  [ApiErrorType.FORBIDDEN]: 'Недостаточно прав для выполнения действия',
  [ApiErrorType.NOT_FOUND]: 'Запрашиваемые данные не найдены',
  [ApiErrorType.SERVER_ERROR]: 'Сервер временно недоступен. Попробуйте позже',
  [ApiErrorType.NETWORK_ERROR]: 'Нет соединения с сервером. Проверьте интернет',
  [ApiErrorType.CANCELLED]: '',
  [ApiErrorType.UNKNOWN]: 'Что-то пошло не так. Попробуйте позже',
};

export function getUserFacingMessage(error: ApiError): string {
  return error.message || FALLBACK_MESSAGES[error.type];
}
