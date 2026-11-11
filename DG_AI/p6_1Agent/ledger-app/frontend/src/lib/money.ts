/**
 * 금액 관련 순수 함수 (NFR-24, FR-10, FR-19).
 * 원 단위 정수만 다루며, 사용률 계산만 소수 한 자리까지 반올림합니다.
 */

export const AMOUNT_MIN = 1;
export const AMOUNT_MAX = 999_999_999;

export type BudgetStatusKey = 'NORMAL' | 'WARNING' | 'EXCEEDED';

/** 천 단위 구분 기호를 붙입니다. 예: 1200000 -> "1,200,000" */
export function groupThousands(value: number): string {
  const sign = value < 0 ? '-' : '';
  const digits = Math.abs(Math.trunc(value)).toString();
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/** 원 단위 표시. 예: 1200000 -> "1,200,000원" */
export function formatKRW(amount: number): string {
  return `${groupThousands(Number.isFinite(amount) ? amount : 0)}원`;
}

/** 입력창에 보여줄 금액 문자열. 숫자 이외의 문자는 버리고 천 단위 구분을 붙입니다. */
export function formatAmountInput(raw: string): string {
  const digits = raw.replace(/\D/g, '').replace(/^0+(?=\d)/, '');
  return digits === '' ? '' : groupThousands(Number(digits));
}

/** 입력창 문자열을 정수로 바꿉니다. 빈 값이면 null. */
export function parseAmountInput(raw: string): number | null {
  const digits = raw.replace(/,/g, '').trim();
  if (digits === '') return null;
  if (!/^\d+$/.test(digits)) return Number.NaN;
  return Number(digits);
}

/**
 * 금액 검증 메시지를 돌려줍니다. 문제가 없으면 null.
 * 서버에서도 같은 규칙으로 다시 검증합니다 (NFR-06).
 */
export function validateAmount(amount: number | null): string | null {
  if (amount === null) return '금액을 입력해 주세요.';
  if (!Number.isInteger(amount)) return '금액은 정수 원 단위로 입력해 주세요.';
  if (amount < AMOUNT_MIN) return '금액은 1원 이상이어야 합니다.';
  if (amount > AMOUNT_MAX) return '금액은 999,999,999원 이하여야 합니다.';
  return null;
}

/** 사용률 (%). 소수 첫째 자리에서 반올림합니다 (FR-19). 금액이 0이면 0. */
export function calcUsagePercent(spent: number, budgetAmount: number): number {
  if (budgetAmount <= 0) return 0;
  return Math.round((spent / budgetAmount) * 1000) / 10;
}

/** 사용률에 따른 상태 (FR-19): 정상 0~79%, 주의 80~99%, 초과 100% 이상. */
export function budgetStatusOf(usagePercent: number): BudgetStatusKey {
  if (usagePercent >= 100) return 'EXCEEDED';
  if (usagePercent >= 80) return 'WARNING';
  return 'NORMAL';
}

/** 화면에 보여줄 정수 퍼센트. 예: 33.3 -> "33%" */
export function formatPercent(percent: number): string {
  return `${Math.round(percent)}%`;
}

/** 상태를 색상과 함께 텍스트와 기호로 표시하기 위한 표시 정보 (NFR-17). */
export const BUDGET_STATUS_META: Record<BudgetStatusKey, { label: string; icon: string }> = {
  NORMAL: { label: '정상', icon: '✓' },
  WARNING: { label: '주의', icon: '!' },
  EXCEEDED: { label: '초과', icon: '×' },
};
