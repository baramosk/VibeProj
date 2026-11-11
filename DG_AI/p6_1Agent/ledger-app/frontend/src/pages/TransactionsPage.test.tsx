import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { renderApp } from '../test/renderApp';
import { TRANSACTIONS } from '../test/fixtures';

describe('거래 목록 화면', () => {
  it('FR-11 거래를 날짜, 유형, 카테고리, 금액으로 표시하고 수입과 지출을 글자로도 구분한다', async () => {
    renderApp('/transactions');

    const table = await screen.findByRole('table', { name: /거래 목록/ });
    expect(within(table).getByText('수입')).toBeInTheDocument();
    expect(within(table).getByText('지출')).toBeInTheDocument();
    expect(within(table).getByText('+3,000,000원')).toBeInTheDocument();
    expect(within(table).getByText('-12,000원')).toBeInTheDocument();
  });

  it('FR-11 거래가 없으면 안내 문구를 보여준다', async () => {
    server.use(
      http.get('*/api/transactions', () => HttpResponse.json({ items: [], total: 0, page: 1, size: 20 })),
    );
    renderApp('/transactions');

    expect(await screen.findByText('거래가 없습니다.')).toBeInTheDocument();
  });

  it('FR-10 필수 항목을 비워 두면 항목별 오류를 보여주고 저장하지 않는다', async () => {
    let created = false;
    server.use(
      http.post('*/api/transactions', () => {
        created = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderApp('/transactions');
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: '거래 기록' }));
    const dialog = screen.getByRole('dialog', { name: '거래 기록' });
    await user.click(within(dialog).getByRole('button', { name: '기록하기' }));

    expect(await within(dialog).findByText('금액을 입력해 주세요.')).toBeInTheDocument();
    expect(within(dialog).getByText('카테고리를 선택해 주세요.')).toBeInTheDocument();
    expect(created).toBe(false);
  });

  it('FR-13 삭제는 확인 창을 거친 뒤에만 DELETE 요청을 보낸다', async () => {
    let deletedId: string | null = null;
    server.use(
      http.delete('*/api/transactions/:id', ({ params }) => {
        deletedId = String(params.id);
        return HttpResponse.json({ budget_status: [] });
      }),
    );
    renderApp('/transactions');
    const user = userEvent.setup();
    const target = TRANSACTIONS[0];
    if (!target) throw new Error('fixture 없음');

    await user.click(await screen.findByRole('button', { name: /식비 12,000원 거래 삭제/ }));
    const dialog = screen.getByRole('dialog', { name: '거래를 삭제할까요?' });
    expect(deletedId).toBeNull();
    expect(within(dialog).getByText(/복구할 수 없습니다/)).toBeInTheDocument();

    await user.click(within(dialog).getByRole('button', { name: '삭제' }));

    await waitFor(() => expect(deletedId).toBe(String(target.id)));
    expect(await screen.findByText('거래를 삭제했습니다.')).toBeInTheDocument();
  });
});
