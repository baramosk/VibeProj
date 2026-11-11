import { useState } from 'react';
import { Link } from 'react-router';
import { getErrorMessage } from '../api/client';
import type { BudgetStatusItem, CategoryType, Transaction, TransactionFilters, TransactionInput } from '../api/types';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/Modal';
import { Pagination } from '../components/ui/Pagination';
import { TypeBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews';
import { MonthNavigator } from '../components/MonthNavigator';
import { useCategoryList } from '../hooks/useCategories';
import { usePageTitle } from '../hooks/usePageTitle';
import { useTransactionManager } from '../hooks/useTransactions';
import { currentYearMonth, formatDateLabel, monthRange } from '../lib/date';
import { formatKRW } from '../lib/money';
import { Field } from '../components/ui/Field';
import { TransactionFormDialog } from './transactions/TransactionFormDialog';

const PAGE_SIZE = 20;

type DialogState = { mode: 'create' } | { mode: 'edit'; target: Transaction } | null;

/** 예산 알림이 새로 생겼는지 안내 문장으로 바꿉니다 (FR-20, FR-21). */
function describeBudgetAlerts(items: BudgetStatusItem[]): string | null {
  const crossed = items.filter((item) => item.new_thresholds.length > 0);
  if (crossed.length === 0) return null;
  const thresholds = crossed.flatMap((item) => item.new_thresholds);
  const hasExceeded = thresholds.includes(100);
  return `${hasExceeded ? '예산을 초과했습니다' : '예산의 80%를 사용했습니다'}. 알림 화면에서 확인할 수 있습니다.`;
}

export function TransactionsPage() {
  usePageTitle('거래');
  const [yearMonth, setYearMonth] = useState(() => currentYearMonth());
  const [typeFilter, setTypeFilter] = useState<'ALL' | CategoryType>('ALL');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);

  const range = monthRange(yearMonth);
  const filters: TransactionFilters = {
    from: range.from,
    to: range.to,
    type: typeFilter === 'ALL' ? undefined : typeFilter,
    category_id: categoryFilter ? Number(categoryFilter) : undefined,
    page,
    size: PAGE_SIZE,
  };

  const txs = useTransactionManager(filters);
  const categories = useCategoryList();

  const [dialog, setDialog] = useState<DialogState>(null);
  const [deleteTarget, setDeleteTarget] = useState<Transaction | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const changeMonth = (next: string) => {
    setYearMonth(next);
    setPage(1);
  };

  const handleSave = async (input: TransactionInput) => {
    if (dialog?.mode === 'edit') {
      const res = await txs.update(dialog.target.id, input);
      setNotice(describeBudgetAlerts(res.budget_status) ?? '거래를 수정했습니다.');
    } else {
      const res = await txs.create(input);
      setNotice(describeBudgetAlerts(res.budget_status) ?? '거래를 기록했습니다.');
    }
    setDialog(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await txs.remove(deleteTarget.id);
      setDeleteTarget(null);
      setNotice(describeBudgetAlerts(res.budget_status) ?? '거래를 삭제했습니다.');
    } catch (error) {
      setDeleteError(getErrorMessage(error, '삭제하지 못했습니다. 다시 시도해 주세요.'));
    } finally {
      setDeleting(false);
    }
  };

  const items = txs.result?.items ?? [];
  const total = txs.result?.total ?? 0;
  const hasFilter = typeFilter !== 'ALL' || categoryFilter !== '';

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>거래</h1>
          <p className="page__description">월별 수입과 지출을 확인하고 기록을 관리합니다.</p>
        </div>
        <Button onClick={() => setDialog({ mode: 'create' })}>거래 기록</Button>
      </header>

      {notice && <Alert variant="success">{notice}</Alert>}

      <section className="card stack" aria-label="거래 조건">
        <div className="filter-bar">
          <div className="field">
            <span className="field__label">기간</span>
            <MonthNavigator value={yearMonth} onChange={changeMonth} />
          </div>
          <Field label="유형">
            {(control) => (
              <select
                {...control}
                name="type"
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value as 'ALL' | CategoryType);
                  setPage(1);
                }}
              >
                <option value="ALL">전체</option>
                <option value="EXPENSE">지출</option>
                <option value="INCOME">수입</option>
              </select>
            )}
          </Field>
          <Field label="카테고리">
            {(control) => (
              <select
                {...control}
                name="category"
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">전체</option>
                {(categories.data ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.type === 'INCOME' ? '수입' : '지출'})
                  </option>
                ))}
              </select>
            )}
          </Field>
        </div>
      </section>

      {txs.loading && !txs.result && <LoadingState message="거래를 불러오는 중입니다." />}
      {Boolean(txs.error) && !txs.result && (
        <ErrorState message={getErrorMessage(txs.error, '거래 목록을 불러오지 못했습니다.')} onRetry={txs.reload} />
      )}

      {txs.result && items.length === 0 && (
        <EmptyState
          title="거래가 없습니다."
          description={
            hasFilter
              ? '선택한 조건에 맞는 거래가 없습니다. 필터를 바꿔 보세요.'
              : '이번 기간에 기록된 거래가 없습니다. 거래 기록 버튼으로 첫 거래를 추가해 보세요.'
          }
          action={
            !hasFilter ? (
              <Link to="/categories" className="btn btn--secondary">
                카테고리 확인하기
              </Link>
            ) : undefined
          }
        />
      )}

      {items.length > 0 && (
        <section className="card" aria-labelledby="tx-list-heading">
          <div className="section-head">
            <h2 id="tx-list-heading" className="section-title">
              거래 목록
            </h2>
            <span className="text-muted" aria-live="polite">
              총 {total.toLocaleString('ko-KR')}건
            </span>
          </div>
          <div className="table-wrap">
            <table className="data-table data-table--stack">
              <caption className="sr-only">{yearMonth} 거래 목록, 날짜 최신순</caption>
              <thead>
                <tr>
                  <th scope="col">날짜</th>
                  <th scope="col">유형</th>
                  <th scope="col">카테고리</th>
                  <th scope="col">메모</th>
                  <th scope="col" className="num">
                    금액
                  </th>
                  <th scope="col">관리</th>
                </tr>
              </thead>
              <tbody>
                {items.map((tx) => {
                  const label = `${formatDateLabel(tx.occurred_on)} ${tx.category_name} ${formatKRW(tx.amount)}`;
                  const sign = tx.type === 'INCOME' ? '+' : '-';
                  return (
                    <tr key={tx.id}>
                      <td data-label="날짜">{formatDateLabel(tx.occurred_on)}</td>
                      <td data-label="유형">
                        <TypeBadge type={tx.type} />
                      </td>
                      <td data-label="카테고리">{tx.category_name}</td>
                      <td data-label="메모" className="memo-cell">
                        {tx.memo ?? <span className="text-muted">없음</span>}
                      </td>
                      <td
                        data-label="금액"
                        className={`num ${tx.type === 'INCOME' ? 'amount-income' : 'amount-expense'}`}
                      >
                        {sign}
                        {formatKRW(tx.amount)}
                      </td>
                      <td data-label="관리">
                        <div className="data-table__actions">
                          <Button
                            variant="secondary"
                            aria-label={`${label} 거래 수정`}
                            onClick={() => setDialog({ mode: 'edit', target: tx })}
                          >
                            수정
                          </Button>
                          <Button
                            variant="danger"
                            aria-label={`${label} 거래 삭제`}
                            onClick={() => {
                              setDeleteError(null);
                              setDeleteTarget(tx);
                            }}
                          >
                            삭제
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            size={PAGE_SIZE}
            total={total}
            onPageChange={setPage}
            disabled={txs.loading}
          />
        </section>
      )}

      {dialog && (
        <TransactionFormDialog
          open
          mode={dialog.mode}
          initial={dialog.mode === 'edit' ? dialog.target : null}
          categories={categories.data ?? []}
          onClose={() => setDialog(null)}
          onSubmit={handleSave}
        />
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="거래를 삭제할까요?"
        message={
          deleteTarget
            ? `${formatDateLabel(deleteTarget.occurred_on)} ${deleteTarget.category_name} ${formatKRW(deleteTarget.amount)} 거래를 삭제합니다. 삭제한 거래는 복구할 수 없습니다.`
            : ''
        }
        confirmLabel="삭제"
        danger
        busy={deleting}
        error={deleteError}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
