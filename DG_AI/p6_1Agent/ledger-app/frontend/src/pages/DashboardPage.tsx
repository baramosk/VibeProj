import { useState } from 'react';
import { Link } from 'react-router';
import { CategoryBreakdownTable, CategoryDonutChart } from '../components/charts/CategoryDonutChart';
import { MonthlyTrendChart, TrendTable } from '../components/charts/MonthlyTrendChart';
import { MonthNavigator } from '../components/MonthNavigator';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews';
import { useExpenseTrend, useMonthlyReport } from '../hooks/useReports';
import { usePageTitle } from '../hooks/usePageTitle';
import { currentYearMonth, formatYearMonthLabel } from '../lib/date';
import { formatKRW } from '../lib/money';
import { getErrorMessage } from '../api/client';

export function DashboardPage() {
  usePageTitle('대시보드');
  const [yearMonth, setYearMonth] = useState(() => currentYearMonth());
  const report = useMonthlyReport(yearMonth);
  const trend = useExpenseTrend(yearMonth);

  const monthLabel = formatYearMonthLabel(yearMonth);
  const data = report.data;

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>대시보드</h1>
          <p className="page__description">{monthLabel}의 수입과 지출을 한눈에 확인합니다.</p>
        </div>
        <MonthNavigator value={yearMonth} onChange={setYearMonth} />
      </header>

      {report.loading && !data && <LoadingState message="월 요약을 불러오는 중입니다." />}
      {Boolean(report.error) && !data && (
        <ErrorState message={getErrorMessage(report.error, '월 요약을 불러오지 못했습니다.')} onRetry={report.reload} />
      )}

      {data && (
        <section aria-labelledby="summary-heading">
          <h2 id="summary-heading" className="sr-only">
            {monthLabel} 요약
          </h2>
          <ul className="grid-3">
            <li className="card summary-card">
              <p className="summary-card__label">수입</p>
              <p className="summary-card__value summary-card__value--income">{formatKRW(data.income_total)}</p>
            </li>
            <li className="card summary-card">
              <p className="summary-card__label">지출</p>
              <p className="summary-card__value summary-card__value--expense">{formatKRW(data.expense_total)}</p>
            </li>
            <li className="card summary-card">
              <p className="summary-card__label">잔액 (수입 - 지출)</p>
              <p className="summary-card__value summary-card__value--balance">{formatKRW(data.balance)}</p>
            </li>
          </ul>
        </section>
      )}

      <div className="grid-2">
        <section className="card" aria-labelledby="category-heading">
          <h2 id="category-heading" className="card__title">
            카테고리별 지출
          </h2>
          {data && data.expense_total > 0 && data.by_category.some((c) => c.amount > 0) ? (
            <div className="stack">
              <CategoryDonutChart items={data.by_category} total={data.expense_total} />
              <div className="table-wrap">
                <CategoryBreakdownTable items={data.by_category} />
              </div>
            </div>
          ) : data ? (
            <EmptyState
              title="이번 달 지출 기록이 없습니다."
              description="거래를 기록하면 카테고리별 비율이 여기에 나타납니다."
              action={
                <Link to="/transactions" className="btn btn--secondary">
                  거래 기록하러 가기
                </Link>
              }
            />
          ) : (
            <LoadingState />
          )}
        </section>

        <section className="card" aria-labelledby="trend-heading">
          <h2 id="trend-heading" className="card__title">
            월별 지출 추이 (최근 12개월)
          </h2>
          {trend.loading && !trend.data && <LoadingState message="추이를 불러오는 중입니다." />}
          {Boolean(trend.error) && !trend.data && (
            <ErrorState message={getErrorMessage(trend.error, '추이를 불러오지 못했습니다.')} onRetry={trend.reload} />
          )}
          {trend.data && (
            <div className="stack">
              <MonthlyTrendChart items={trend.data.items} />
              <div className="table-wrap">
                <TrendTable items={trend.data.items} />
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
