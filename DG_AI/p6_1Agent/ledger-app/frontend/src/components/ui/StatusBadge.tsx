import { BUDGET_STATUS_META, type BudgetStatusKey } from '../../lib/money';

/** 예산 상태 배지. 색상, 기호, 텍스트를 함께 씁니다 (FR-19, NFR-17). */
export function BudgetStatusBadge({ status }: { status: BudgetStatusKey }) {
  const meta = BUDGET_STATUS_META[status];
  return (
    <span className={`badge badge--${status.toLowerCase()}`}>
      <span className="badge__icon" aria-hidden="true">
        {meta.icon}
      </span>
      {meta.label}
    </span>
  );
}

/** 거래 유형 표시. 수입과 지출을 글자로 구분합니다. */
export function TypeBadge({ type }: { type: 'INCOME' | 'EXPENSE' }) {
  return (
    <span className={`badge badge--${type === 'INCOME' ? 'income' : 'expense'}`}>
      {type === 'INCOME' ? '수입' : '지출'}
    </span>
  );
}
