import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { ApiError, api, getErrorMessage, getFieldErrors, setCsrfToken } from './client';

describe('API 클라이언트', () => {
  it('NFR-05 상태 변경 요청에는 X-CSRF-Token 헤더를 붙인다', async () => {
    setCsrfToken('token-123');
    let receivedToken: string | null = null;
    let receivedCookieMode: RequestCredentials | undefined;
    server.use(
      http.post('*/api/categories', ({ request }) => {
        receivedToken = request.headers.get('X-CSRF-Token');
        receivedCookieMode = request.credentials;
        return HttpResponse.json({ id: 9 }, { status: 201 });
      }),
    );

    await api.post('/categories', { body: { name: '간식', type: 'EXPENSE', color: '#000000' } });

    expect(receivedToken).toBe('token-123');
    expect(receivedCookieMode).toBe('include');
    setCsrfToken(null);
  });

  it('NFR-05 조회 요청에는 CSRF 헤더를 붙이지 않는다', async () => {
    setCsrfToken('token-123');
    let receivedToken: string | null = 'unset';
    server.use(
      http.get('*/api/categories', ({ request }) => {
        receivedToken = request.headers.get('X-CSRF-Token');
        return HttpResponse.json([]);
      }),
    );

    await api.get('/categories');

    expect(receivedToken).toBeNull();
    setCsrfToken(null);
  });

  it('API 계약 오류 형식 { error: { code, message, details } } 을 ApiError로 바꾼다', async () => {
    server.use(
      http.post('*/api/budgets', () =>
        HttpResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: '입력값을 확인해 주세요.',
              details: { amount: '금액은 1원 이상이어야 합니다.' },
            },
          },
          { status: 400 },
        ),
      ),
    );

    const error = await api.post('/budgets', { body: { amount: 0 } }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(400);
    expect((error as ApiError).code).toBe('VALIDATION_ERROR');
    expect(getErrorMessage(error)).toBe('입력값을 확인해 주세요.');
    expect(getFieldErrors(error)).toEqual({ amount: '금액은 1원 이상이어야 합니다.' });
  });

  it('API 계약 409 중복 응답을 CONFLICT로 구분한다', async () => {
    server.use(
      http.post('*/api/budgets', () =>
        HttpResponse.json({ error: { code: 'CONFLICT', message: '이미 설정된 예산입니다.', details: {} } }, { status: 409 }),
      ),
    );

    const error = await api.post('/budgets', { body: {} }).catch((e: unknown) => e);

    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).code).toBe('CONFLICT');
  });

  it('오류 본문이 JSON이 아니어도 상태별 기본 문장으로 처리한다', async () => {
    server.use(http.get('*/api/reports/monthly', () => new HttpResponse('<html>bad gateway</html>', { status: 502 })));

    const error = await api.get('/reports/monthly').catch((e: unknown) => e);

    expect((error as ApiError).status).toBe(502);
    expect(getErrorMessage(error)).toBe('일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
  });

  it('204 응답은 본문 없이 성공으로 처리한다', async () => {
    server.use(http.post('*/api/auth/logout', () => new HttpResponse(null, { status: 204 })));

    await expect(api.post<void>('/auth/logout')).resolves.toBeUndefined();
  });
});
