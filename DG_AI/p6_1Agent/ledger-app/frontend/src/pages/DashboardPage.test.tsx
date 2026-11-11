import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../test/renderApp';

describe('대시보드 화면', () => {
  it('FR-15 월 요약 카드에 수입, 지출, 잔액을 원 단위로 표시한다', async () => {
    renderApp('/dashboard');

    expect(await screen.findByText('3,000,000원')).toBeInTheDocument();
    expect(screen.getByText('1,800,000원')).toBeInTheDocument();
    expect(screen.getByText('잔액 (수입 - 지출)')).toBeInTheDocument();
  });

  it('FR-16 도넛 차트와 같은 내용의 표를 금액 내림차순으로 제공한다 (NFR-17)', async () => {
    renderApp('/dashboard');

    const table = await screen.findByRole('table', { name: '카테고리별 지출 표 (금액 내림차순)' });
    const rows = within(table).getAllByRole('row');
    // rows[0]은 머리글. 금액이 큰 교통(800,000원)이 먼저 나옵니다.
    expect(rows[1]).toHaveTextContent('교통');
    expect(rows[1]).toHaveTextContent('800,000원');
    expect(rows[1]).toHaveTextContent('67%');
    expect(rows[2]).toHaveTextContent('식비');
    expect(rows[2]).toHaveTextContent('33%');
  });

  it('FR-17 최근 12개월 막대 그래프와 같은 내용의 표를 제공한다 (거래 없는 달은 0원)', async () => {
    renderApp('/dashboard');

    const table = await screen.findByRole('table', { name: '월별 지출 표 (최근 12개월)' });
    const rows = within(table).getAllByRole('row');
    expect(rows).toHaveLength(13);
    expect(rows[12]).toHaveTextContent('2026-11');
    expect(rows[12]).toHaveTextContent('1,200,000원');
    expect(rows[1]).toHaveTextContent('2025-12');
    expect(rows[1]).toHaveTextContent('0원');
  });
});
