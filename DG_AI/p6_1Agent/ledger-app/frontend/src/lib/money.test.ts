import { describe, expect, it } from 'vitest';
import {
  budgetStatusOf,
  calcUsagePercent,
  formatAmountInput,
  formatKRW,
  formatPercent,
  parseAmountInput,
  validateAmount,
} from './money';

describe('금액 포맷 (NFR-24)', () => {
  it('NFR-24 원 단위 천 단위 구분으로 표시한다', () => {
    expect(formatKRW(1200000)).toBe('1,200,000원');
    expect(formatKRW(0)).toBe('0원');
    expect(formatKRW(999)).toBe('999원');
    expect(formatKRW(-1800)).toBe('-1,800원');
  });

  it('NFR-24 입력 문자열에서 숫자만 남기고 천 단위 구분을 붙인다', () => {
    expect(formatAmountInput('0012000')).toBe('12,000');
    expect(formatAmountInput('12a,000')).toBe('12,000');
    expect(formatAmountInput('')).toBe('');
    expect(parseAmountInput('1,200,000')).toBe(1200000);
    expect(parseAmountInput('')).toBeNull();
    expect(Number.isNaN(parseAmountInput('1.5'))).toBe(true);
  });
});

describe('금액 검증 (FR-10)', () => {
  it('FR-10 1원 이상 999,999,999원 이하 정수만 통과시킨다', () => {
    expect(validateAmount(1)).toBeNull();
    expect(validateAmount(999_999_999)).toBeNull();
    expect(validateAmount(0)).toBe('금액은 1원 이상이어야 합니다.');
    expect(validateAmount(-5)).toBe('금액은 1원 이상이어야 합니다.');
    expect(validateAmount(1_000_000_000)).toBe('금액은 999,999,999원 이하여야 합니다.');
    expect(validateAmount(1.5)).toBe('금액은 정수 원 단위로 입력해 주세요.');
    expect(validateAmount(null)).toBe('금액을 입력해 주세요.');
  });
});

describe('예산 사용률과 상태 (FR-19, FR-20)', () => {
  it('FR-19 79.4%는 정상, 80%는 주의, 100%는 초과로 판정한다 (경계값)', () => {
    expect(budgetStatusOf(79.4)).toBe('NORMAL');
    expect(budgetStatusOf(79.9)).toBe('NORMAL');
    expect(budgetStatusOf(80)).toBe('WARNING');
    expect(budgetStatusOf(99.9)).toBe('WARNING');
    expect(budgetStatusOf(100)).toBe('EXCEEDED');
    expect(budgetStatusOf(100.1)).toBe('EXCEEDED');
  });

  it('FR-19 사용률은 소수 첫째 자리까지 반올림한다', () => {
    expect(calcUsagePercent(794, 1000)).toBe(79.4);
    expect(calcUsagePercent(1, 3)).toBe(33.3);
    expect(calcUsagePercent(2, 3)).toBe(66.7);
    expect(calcUsagePercent(500, 0)).toBe(0);
  });

  it('FR-19 화면 표시는 정수 퍼센트로 한다', () => {
    expect(formatPercent(33.3)).toBe('33%');
    expect(formatPercent(79.5)).toBe('80%');
  });
});
