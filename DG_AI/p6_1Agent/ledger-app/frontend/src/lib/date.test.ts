import { describe, expect, it } from 'vitest';
import {
  currentYearMonth,
  formatYearMonthLabel,
  isFutureDate,
  isFutureMonth,
  isValidDate,
  monthRange,
  shiftMonth,
  todayKST,
} from './date';

// 2026-11-06 12:00 KST (UTC 03:00)
const NOW = new Date('2026-11-06T03:00:00Z');

describe('월 이동과 범위 (FR-14)', () => {
  it('FR-14 연도 경계를 넘어 월을 이동한다', () => {
    expect(shiftMonth('2026-01', -1)).toBe('2025-12');
    expect(shiftMonth('2026-12', 1)).toBe('2027-01');
    expect(shiftMonth('2026-11', 0)).toBe('2026-11');
  });

  it('FR-14 월의 첫날과 말일을 계산한다 (윤년 포함)', () => {
    expect(monthRange('2026-12')).toEqual({ from: '2026-12-01', to: '2026-12-31' });
    expect(monthRange('2028-02')).toEqual({ from: '2028-02-01', to: '2028-02-29' });
    expect(monthRange('2026-02')).toEqual({ from: '2026-02-01', to: '2026-02-28' });
  });

  it('FR-14 미래 월은 선택할 수 없다고 판정한다', () => {
    expect(isFutureMonth('2026-12', NOW)).toBe(true);
    expect(isFutureMonth('2026-11', NOW)).toBe(false);
    expect(isFutureMonth('2026-10', NOW)).toBe(false);
  });

  it('FR-14 표시용 월 이름을 만든다', () => {
    expect(formatYearMonthLabel('2026-11')).toBe('2026년 11월');
  });
});

describe('서울 기준 날짜 (NFR-24, R-05)', () => {
  it('NFR-24 UTC 자정 전이라도 서울 날짜 기준으로 오늘을 판단한다', () => {
    // 2026-11-05 23:30 UTC = 2026-11-06 08:30 KST
    const lateUtc = new Date('2026-11-05T23:30:00Z');
    expect(todayKST(lateUtc)).toBe('2026-11-06');
    expect(currentYearMonth(lateUtc)).toBe('2026-11');
  });

  it('FR-10 미래 날짜 입력을 판정한다', () => {
    expect(isFutureDate('2026-11-07', NOW)).toBe(true);
    expect(isFutureDate('2026-11-06', NOW)).toBe(false);
  });

  it('FR-10 존재하지 않는 날짜를 거른다', () => {
    expect(isValidDate('2026-02-30')).toBe(false);
    expect(isValidDate('2028-02-29')).toBe(true);
    expect(isValidDate('2026-13-01')).toBe(false);
  });
});
