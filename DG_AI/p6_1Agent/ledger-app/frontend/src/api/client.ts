/**
 * 얇은 HTTP 클라이언트.
 * - 쿠키(세션)를 항상 함께 보냅니다 (credentials: include).
 * - POST, PUT, PATCH, DELETE 에는 X-CSRF-Token 헤더를 붙입니다 (NFR-05).
 * - 오류 형식 { error: { code, message, details } } 을 ApiError로 바꿉니다.
 */

import type { ApiErrorBody, ErrorCode } from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
}

const API_BASE = '/api';
const UNSAFE_METHODS: ReadonlySet<Method> = new Set<Method>(['POST', 'PUT', 'PATCH', 'DELETE']);

const FALLBACK_MESSAGES: Record<number, string> = {
  400: '입력값을 다시 확인해 주세요.',
  401: '로그인이 필요합니다.',
  403: '요청을 처리할 수 없습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.',
  404: '요청한 항목을 찾을 수 없습니다.',
  409: '이미 같은 항목이 있습니다.',
  423: '로그인이 일시적으로 잠겼습니다. 잠시 후 다시 시도해 주세요.',
};

const NETWORK_MESSAGE = '서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.';
const SERVER_MESSAGE = '일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';

let csrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

/** 로그인, 가입, GET /api/auth/me 응답의 csrf_token을 저장합니다. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function getCsrfToken(): string | null {
  return csrfToken;
}

/** 세션이 만료되어 401을 받았을 때 호출될 처리기를 등록합니다 (AuthProvider가 씁니다). */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** 화면에 보여줄 오류 문장을 고릅니다. 어떤 값이 와도 문자열을 돌려줍니다. */
export function getErrorMessage(error: unknown, fallback = SERVER_MESSAGE): string {
  if (isApiError(error)) return error.message || fallback;
  return fallback;
}

/** 입력 검증 오류(details)에서 필드별 메시지를 꺼냅니다. 값이 문자열인 항목만 씁니다. */
export function getFieldErrors(error: unknown): Record<string, string> {
  if (!isApiError(error)) return {};
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(error.details)) {
    if (typeof value === 'string') result[key] = value;
  }
  return result;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === '') continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ''}`;
}

async function parseErrorBody(response: Response): Promise<ApiErrorBody | null> {
  try {
    return (await response.json()) as ApiErrorBody;
  } catch {
    return null;
  }
}

export async function request<T>(method: Method, path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  let body: string | undefined;

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.body);
  }
  if (UNSAFE_METHODS.has(method) && csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      headers,
      body,
      credentials: 'include',
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'NETWORK_ERROR', NETWORK_MESSAGE);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await parseErrorBody(response);

  if (!response.ok) {
    const status = response.status;
    const code = payload?.error?.code ?? defaultCode(status);
    const message = payload?.error?.message ?? FALLBACK_MESSAGES[status] ?? SERVER_MESSAGE;
    const details = payload?.error?.details ?? {};
    if (status === 401) unauthorizedHandler?.();
    throw new ApiError(status, code, message, details);
  }

  return payload as T;
}

function defaultCode(status: number): ErrorCode | string {
  switch (status) {
    case 400:
      return 'VALIDATION_ERROR';
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 409:
      return 'CONFLICT';
    case 423:
      return 'ACCOUNT_LOCKED';
    default:
      return status >= 500 ? 'INTERNAL_ERROR' : 'UNKNOWN';
  }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>('GET', path, options),
  post: <T>(path: string, options?: RequestOptions) => request<T>('POST', path, options),
  put: <T>(path: string, options?: RequestOptions) => request<T>('PUT', path, options),
  patch: <T>(path: string, options?: RequestOptions) => request<T>('PATCH', path, options),
  delete: <T>(path: string, options?: RequestOptions) => request<T>('DELETE', path, options),
};
