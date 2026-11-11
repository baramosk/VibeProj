import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { renderApp } from '../test/renderApp';

describe('예산 화면', () => {
  it('FR-19 예산별 진행 막대와 사용 금액, 사용률 텍스트를 보여준다', async () => {
    renderApp('/budgets?month=2026-11');

    const bar = await screen.findByRole('progressbar', { name: '식비 사용률' });
    expect(bar).toHaveAttribute('aria-valuenow', '80');
    expect(bar).toHaveAttribute('aria-valuetext', '80%');
    expect(screen.getByText('400,000원 / 500,000원 (80%)')).toBeInTheDocument();
  });

  it('FR-19 상태를 색상과 함께 텍스트로 표시한다 (주의, 초과)', async () => {
    renderApp('/budgets?month=2026-11');

    expect(await screen.findByText('주의')).toBeInTheDocument();
    expect(screen.getByText('초과')).toBeInTheDocument();
  });

  it('FR-18 같은 대상과 월에 예산이 있으면 409를 받아 덮어쓰기 확인 창을 띄운다', async () => {
    server.use(
      http.post('*/api/budgets', () =>
        HttpResponse.json(
          { error: { code: 'CONFLICT', message: '이미 설정된 예산입니다.', details: {} } },
          { status: 409 },
        ),
      ),
    );
    renderApp('/budgets?month=2026-11');
    const user = userEvent.setup();

    await screen.findByRole('progressbar', { name: '식비 사용률' });
    const form = screen.getByRole('heading', { name: '예산 설정' }).closest('section');
    if (!form) throw new Error('예산 설정 영역 없음');
    await user.type(within(form).getByLabelText(/금액/), '300000');
    await user.click(within(form).getByRole('button', { name: '예산 설정' }));

    const dialog = await screen.findByRole('dialog', { name: '기존 예산을 덮어쓸까요?' });
    expect(within(dialog).getByRole('button', { name: '덮어쓰기' })).toBeInTheDocument();
  });
});
