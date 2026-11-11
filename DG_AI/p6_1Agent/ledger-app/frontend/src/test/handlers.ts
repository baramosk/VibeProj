import { http, HttpResponse } from 'msw';
import {
  BUDGETS,
  CATEGORIES,
  MONTHLY_REPORT,
  NOTIFICATIONS,
  TRANSACTIONS,
  USER,
  makeTrend,
} from './fixtures';

/**
 * 기본 응답. 기본값은 로그인된 상태입니다.
 * 특정 테스트는 server.use(...)로 덮어씁니다.
 */
export const defaultHandlers = [
  http.get('*/api/auth/me', () => HttpResponse.json({ user: USER, csrf_token: 'csrf-test' })),
  http.get('*/api/categories', () => HttpResponse.json(CATEGORIES)),
  http.get('*/api/transactions', () =>
    HttpResponse.json({ items: TRANSACTIONS, total: TRANSACTIONS.length, page: 1, size: 20 }),
  ),
  http.get('*/api/reports/monthly', () => HttpResponse.json(MONTHLY_REPORT)),
  http.get('*/api/reports/trend', ({ request }) => {
    const end = new URL(request.url).searchParams.get('end') ?? '2026-11';
    return HttpResponse.json({ items: makeTrend(end) });
  }),
  http.get('*/api/budgets', () => HttpResponse.json(BUDGETS)),
  http.get('*/api/notifications', () => HttpResponse.json(NOTIFICATIONS)),
];

/** 로그인하지 않은 상태의 응답 (세션 없음) */
export const unauthenticatedHandler = http.get('*/api/auth/me', () =>
  HttpResponse.json(
    { error: { code: 'UNAUTHORIZED', message: '로그인이 필요합니다.', details: {} } },
    { status: 401 },
  ),
);
