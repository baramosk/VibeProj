import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { unauthenticatedHandler } from '../test/handlers';
import { renderApp } from '../test/renderApp';

async function openSignup() {
  server.use(unauthenticatedHandler);
  renderApp('/signup');
  return screen.findByRole('heading', { name: '회원가입', level: 1 });
}

describe('회원가입 화면', () => {
  it('FR-01 비밀번호 규칙과 확인 일치를 항목별 메시지로 보여준다', async () => {
    await openSignup();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/이메일/), 'new@example.com');
    await user.type(screen.getByLabelText(/^비밀번호/, { selector: 'input[name="password"]' }), 'abcdefgh');
    await user.type(screen.getByLabelText(/비밀번호 확인/), 'abcdefgh');
    await user.type(screen.getByLabelText(/닉네임/), '가계');
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }));

    expect(await screen.findByText('비밀번호에는 영문과 숫자가 모두 포함되어야 합니다.')).toBeInTheDocument();
  });

  it('FR-01 이메일 중복(409)은 이메일 필드 아래에 표시한다', async () => {
    server.use(
      http.post('*/api/auth/signup', () =>
        HttpResponse.json(
          { error: { code: 'CONFLICT', message: '이미 가입된 이메일입니다.', details: {} } },
          { status: 409 },
        ),
      ),
    );
    await openSignup();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText(/이메일/), 'user@example.com');
    await user.type(screen.getByLabelText(/^비밀번호/, { selector: 'input[name="password"]' }), 'abc12345');
    await user.type(screen.getByLabelText(/비밀번호 확인/), 'abc12345');
    await user.type(screen.getByLabelText(/닉네임/), '가계');
    await user.click(screen.getByRole('button', { name: '가입하고 시작하기' }));

    const email = screen.getByLabelText(/이메일/);
    expect(await screen.findByText('이미 가입된 이메일입니다.')).toBeInTheDocument();
    expect(email).toHaveAttribute('aria-invalid', 'true');
  });
});
