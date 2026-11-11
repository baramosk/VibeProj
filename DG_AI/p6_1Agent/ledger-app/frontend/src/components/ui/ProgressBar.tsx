import { formatPercent, type BudgetStatusKey } from '../../lib/money';

interface ProgressBarProps {
  label: string;
  percent: number;
  status: BudgetStatusKey;
}

/**
 * 예산 진행 막대. 값은 role="progressbar"로 전달합니다.
 * 막대 색은 상태에 따라 바뀌지만, 옆 텍스트에도 같은 상태를 적습니다 (NFR-17).
 */
export function ProgressBar({ label, percent, status }: ProgressBarProps) {
  const clamped = Math.min(Math.max(percent, 0), 100);
  return (
    <div
      className="progress"
      role="progressbar"
      aria-label={`${label} 사용률`}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(clamped)}
      aria-valuetext={formatPercent(percent)}
    >
      <div className={`progress__fill progress__fill--${status.toLowerCase()}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
