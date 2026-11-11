import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from './server';

// Recharts의 ResponsiveContainer가 요구하는 ResizeObserver는 jsdom에 없으므로 빈 구현을 둡니다.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;

// 브라우저의 fetch는 상대 경로를 현재 주소 기준으로 풀지만, Node의 fetch는 그렇지 않습니다.
// 테스트에서만 /api 상대 경로를 jsdom의 현재 주소로 바꿔 줍니다.
const nodeFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
  if (typeof input === 'string' && input.startsWith('/')) {
    return nodeFetch(new URL(input, window.location.href), init);
  }
  return nodeFetch(input, init);
}) as typeof fetch;

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.restoreAllMocks();
});

afterAll(() => server.close());
