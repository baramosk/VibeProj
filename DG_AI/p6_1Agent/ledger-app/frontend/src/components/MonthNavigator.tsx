import { currentYearMonth, formatYearMonthLabel, isFutureMonth, shiftMonth } from '../lib/date';
import { Button } from './ui/Button';

interface MonthNavigatorProps {
  value: string;
  onChange: (yearMonth: string) => void;
}

/** 월 이동 (FR-14). 미래 월은 선택할 수 없습니다. */
export function MonthNavigator({ value, onChange }: MonthNavigatorProps) {
  const nextMonth = shiftMonth(value, 1);
  const canGoNext = !isFutureMonth(nextMonth);
  const thisMonth = currentYearMonth();

  return (
    <div className="month-nav">
      <Button variant="secondary" aria-label="이전 달" onClick={() => onChange(shiftMonth(value, -1))}>
        &lsaquo;
      </Button>
      <div className="month-nav__center">
        <span className="month-nav__label" aria-live="polite">
          {formatYearMonthLabel(value)}
        </span>
        <input
          type="month"
          className="month-nav__input"
          aria-label="월 선택"
          value={value}
          max={thisMonth}
          onChange={(event) => {
            if (event.target.value && !isFutureMonth(event.target.value)) onChange(event.target.value);
          }}
        />
      </div>
      <Button variant="secondary" aria-label="다음 달" onClick={() => onChange(nextMonth)} disabled={!canGoNext}>
        &rsaquo;
      </Button>
    </div>
  );
}
