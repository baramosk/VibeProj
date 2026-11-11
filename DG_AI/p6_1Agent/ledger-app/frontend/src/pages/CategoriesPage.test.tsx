import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { renderApp } from '../test/renderApp';

describe('카테고리 관리 화면', () => {
  it('FR-06 기본 카테고리를 유형별 목록에 표시하고 기본 표시를 붙인다', async () => {
    renderApp('/categories');

    const expenseSection = await screen.findByRole('region', { name: /지출 카테고리/ });
    expect(within(expenseSection).getByText('식비')).toBeInTheDocument();
    expect(within(expenseSection).getAllByText('기본')).toHaveLength(2);
    expect(screen.getByRole('region', { name: /수입 카테고리/ })).toBeInTheDocument();
  });

  it('FR-07 이름이 비어 있으면 저장하지 않고 오류를 보여준다', async () => {
    let created = false;
    server.use(
      http.post('*/api/categories', () => {
        created = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderApp('/categories');
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: '추가' }));

    expect(await screen.findByText('카테고리 이름을 입력해 주세요.')).toBeInTheDocument();
    expect(created).toBe(false);
  });

  it('FR-07 같은 유형 안의 중복 이름은 서버 메시지를 그대로 보여준다 (409)', async () => {
    server.use(
      http.post('*/api/categories', () =>
        HttpResponse.json(
          { error: { code: 'CONFLICT', message: '같은 이름의 카테고리가 이미 있습니다.', details: {} } },
          { status: 409 },
        ),
      ),
    );
    renderApp('/categories');
    const user = userEvent.setup();

    await user.type(await screen.findByLabelText(/이름/), '식비');
    await user.click(screen.getByRole('button', { name: '추가' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('같은 이름의 카테고리가 이미 있습니다.');
  });
});
