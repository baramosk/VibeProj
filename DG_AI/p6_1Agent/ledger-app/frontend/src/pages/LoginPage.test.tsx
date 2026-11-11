import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { unauthenticatedHandler } from '../test/handlers';
import { renderApp } from '../test/renderApp';

describe('로그인 화면', () => {
  it('FR-02 로그인 실패 시 계정 존재 여부를 드러내지 않는 고정 문구를 보여준다', async () => {
    server.use(
      unauthenticatedHandler,
      http.post('*/api/auth/login', () =>
        HttpResponse.json(
          { error: { code: 'UNAUTHORIZED', message: '이메일 또는 비밀번호가 올바르지 않습니다.', details: {} } },
          { status: 401 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp('/login');

    await user.type(await screen.findByLabelText(/이메일/), 'nobody@example.com');
    await user.type(screen.getByLabelText(/비밀번호/), 'wrong12345');
    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('이메일 또는 비밀번호가 올바르지 않습니다.');
  });

  it('NFR-18 이메일 형식이 잘못되면 API를 호출하지 않고 필드 옆에 오류를 붙인다', async () => {
    let loginCalled = false;
    server.use(
      unauthenticatedHandler,
      http.post('*/api/auth/login', () => {
        loginCalled = true;
        return HttpResponse.json({});
      }),
    );
    const user = userEvent.setup();
    renderApp('/login');

    const email = await screen.findByLabelText(/이메일/);
    await user.type(email, 'not-an-email');
    await user.type(screen.getByLabelText(/비밀번호/), 'x');
    await user.click(screen.getByRole('button', { name: '로그인' }));

    expect(await screen.findByText('이메일 형식이 올바르지 않습니다.')).toBeInTheDocument();
    expect(email).toHaveAttribute('aria-invalid', 'true');
    expect(email).toHaveAccessibleDescription(/이메일 형식이 올바르지 않습니다/);
    expect(loginCalled).toBe(false);
  });

  it('FR-02 로그인 상태에서 로그인 화면에 오면 대시보드로 보낸다', async () => {
    renderApp('/login');

    expect(await screen.findByRole('heading', { name: '대시보드' })).toBeInTheDocument();
  });
});

describe('보호 화면 접근 (FR-03)', () => {
  it('FR-03 로그인하지 않은 사용자는 보호 화면에서 로그인 화면으로 이동한다', async () => {
    server.use(unauthenticatedHandler);
    renderApp('/transactions');

    await waitFor(() => expect(screen.getByRole('heading', { name: '로그인', level: 1 })).toBeInTheDocument());
  });
});
