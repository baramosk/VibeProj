import { useRef, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router';
import { ApiError, getErrorMessage, getFieldErrors, isApiError } from '../api/client';
import type { Budget } from '../api/types';
import { MonthNavigator } from '../components/MonthNavigator';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { ConfirmDialog, Modal } from '../components/ui/Modal';
import { ProgressBar } from '../components/ui/ProgressBar';
import { BudgetStatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews';
import { useBudgetManager } from '../hooks/useBudgets';
import { useCategoryList } from '../hooks/useCategories';
import { usePageTitle } from '../hooks/usePageTitle';
import { currentYearMonth, formatYearMonthLabel, isFutureMonth, isValidYearMonth } from '../lib/date';
import { focusFirstInvalid } from '../lib/focus';
import { formatAmountInput, formatKRW, formatPercent, parseAmountInput, validateAmount } from '../lib/money';

/** 대상 선택의 빈 값은 "전체 지출" 예산을 뜻합니다 (A-08). */
const ALL_EXPENSE = '';

function budgetTargetName(budget: Budget): string {
  return budget.category_name ?? '전체 지출';
}

interface PendingOverwrite {
  categoryId: number | null;
  amount: number;
  targetName: string;
}

export function BudgetsPage() {
  usePageTitle('예산');
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get('month');
  const yearMonth = requested && isValidYearMonth(requested) && !isFutureMonth(requested) ? requested : currentYearMonth();

  const setMonth = (next: string) => {
    setSearchParams({ month: next }, { replace: true });
  };

  const manager = useBudgetManager(yearMonth);
  const categories = useCategoryList('EXPENSE');

  const [editing, setEditing] = useState<Budget | null>(null);
  const [deleting, setDeleting] = useState<Budget | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingOverwrite | null>(null);
  const [overwriteBusy, setOverwriteBusy] = useState(false);
  const [overwriteError, setOverwriteError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await manager.remove(deleting.id);
      setNotice(`${budgetTargetName(deleting)} 예산을 삭제했습니다.`);
      setDeleting(null);
    } catch (error) {
      setDeleteError(getErrorMessage(error, '삭제하지 못했습니다. 다시 시도해 주세요.'));
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleOverwrite = async () => {
    if (!pending) return;
    setOverwriteBusy(true);
    setOverwriteError(null);
    try {
      const done = await manager.overwriteBudget(pending.categoryId, pending.amount);
      if (!done) {
        setOverwriteError('기존 예산을 찾지 못했습니다. 목록을 새로 불러왔으니 다시 시도해 주세요.');
        return;
      }
      setNotice(`${pending.targetName} 예산을 ${formatKRW(pending.amount)}으로 바꿨습니다.`);
      setPending(null);
    } catch (error) {
      setOverwriteError(getErrorMessage(error, '덮어쓰지 못했습니다. 다시 시도해 주세요.'));
    } finally {
      setOverwriteBusy(false);
    }
  };

  const budgets = manager.budgets;

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>예산</h1>
          <p className="page__description">
            {formatYearMonthLabel(yearMonth)}의 전체 지출 또는 지출 카테고리별 예산과 사용률입니다.
          </p>
        </div>
        <MonthNavigator value={yearMonth} onChange={setMonth} />
      </header>

      {notice && <Alert variant="success">{notice}</Alert>}

      <BudgetCreateForm
        key={yearMonth}
        categories={categories.data ?? []}
        onCreate={async (categoryId, amount) => {
          try {
            await manager.create({ amount, category_id: categoryId ?? undefined });
            setNotice(`${categoryId === null ? '전체 지출' : nameOf(categories.data, categoryId)} 예산을 설정했습니다.`);
          } catch (error) {
            if (isApiError(error) && error.status === 409) {
              setPending({
                categoryId,
                amount,
                targetName: categoryId === null ? '전체 지출' : nameOf(categories.data, categoryId),
              });
              setOverwriteError(null);
              return;
            }
            throw error;
          }
        }}
      />

      {manager.loading && budgets.length === 0 && <LoadingState message="예산을 불러오는 중입니다." />}
      {Boolean(manager.error) && budgets.length === 0 && (
        <ErrorState message={getErrorMessage(manager.error, '예산을 불러오지 못했습니다.')} onRetry={manager.reload} />
      )}

      {!manager.loading && !manager.error && budgets.length === 0 && (
        <EmptyState
          title="이번 달 설정된 예산이 없습니다."
          description="위에서 전체 지출 또는 카테고리 예산을 설정하면 사용률이 여기에 나타납니다."
        />
      )}

      {budgets.length > 0 && (
        <section aria-labelledby="budget-list-heading">
          <h2 id="budget-list-heading" className="form-section-title">
            예산 목록
          </h2>
          <ul className="budget-list budget-list--spaced">
            {budgets.map((budget) => {
              const name = budgetTargetName(budget);
              return (
                <li key={budget.id} className="budget-item" id={`budget-${budget.id}`}>
                  <div className="budget-item__head">
                    <span className="budget-item__name">
                      {name}
                    </span>
                    <BudgetStatusBadge status={budget.status} />
                  </div>
                  <ProgressBar label={name} percent={budget.usage_percent} status={budget.status} />
                  <p className="budget-item__figures">
                    {formatKRW(budget.spent)} / {formatKRW(budget.amount)} ({formatPercent(budget.usage_percent)})
                  </p>
                  <div className="budget-item__actions">
                    <Button variant="secondary" aria-label={`${name} 예산 금액 수정`} onClick={() => setEditing(budget)}>
                      금액 수정
                    </Button>
                    <Button
                      variant="danger"
                      aria-label={`${name} 예산 삭제`}
                      onClick={() => {
                        setDeleteError(null);
                        setDeleting(budget);
                      }}
                    >
                      삭제
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {editing && (
        <BudgetAmountDialog
          budget={editing}
          onClose={() => setEditing(null)}
          onSave={async (amount) => {
            await manager.updateAmount(editing.id, amount);
            setNotice(`${budgetTargetName(editing)} 예산 금액을 ${formatKRW(amount)}으로 바꿨습니다.`);
            setEditing(null);
          }}
        />
      )}

      <ConfirmDialog
        open={deleting !== null}
        title="예산을 삭제할까요?"
        message={deleting ? `${budgetTargetName(deleting)} 예산을 삭제합니다. 거래 기록은 그대로 남습니다.` : ''}
        confirmLabel="삭제"
        danger
        busy={deleteBusy}
        error={deleteError}
        onConfirm={handleDelete}
        onCancel={() => setDeleting(null)}
      />

      <ConfirmDialog
        open={pending !== null}
        title="기존 예산을 덮어쓸까요?"
        message={
          pending
            ? `${pending.targetName} 예산이 이미 ${formatYearMonthLabel(yearMonth)}에 있습니다. 금액을 ${formatKRW(pending.amount)}으로 바꿉니다.`
            : ''
        }
        confirmLabel="덮어쓰기"
        busy={overwriteBusy}
        error={overwriteError}
        onConfirm={handleOverwrite}
        onCancel={() => setPending(null)}
      />
    </div>
  );
}

function nameOf(categories: { id: number; name: string }[] | undefined, id: number): string {
  return categories?.find((c) => c.id === id)?.name ?? '카테고리';
}

function BudgetCreateForm({
  categories,
  onCreate,
}: {
  categories: { id: number; name: string }[];
  onCreate: (categoryId: number | null, amount: number) => Promise<void>;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [target, setTarget] = useState(ALL_EXPENSE);
  const [amountText, setAmountText] = useState('');
  const [targetError, setTargetError] = useState<string | null>(null);
  const [amountError, setAmountError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const amount = parseAmountInput(amountText);
    const nextAmountError = Number.isNaN(amount) ? '금액은 숫자로 입력해 주세요.' : validateAmount(amount);
    setAmountError(nextAmountError);
    const nextTargetError =
      target !== ALL_EXPENSE && !categories.some((c) => String(c.id) === target) ? '대상을 다시 선택해 주세요.' : null;
    setTargetError(nextTargetError);
    if (nextAmountError || amount === null || nextTargetError) {
      focusFirstInvalid(formRef.current);
      return;
    }

    setSubmitting(true);
    try {
      await onCreate(target === ALL_EXPENSE ? null : Number(target), amount);
      setAmountText('');
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (fieldErrors.amount) setAmountError(fieldErrors.amount);
      if (fieldErrors.category_id) setTargetError(fieldErrors.category_id);
      if (!fieldErrors.amount && !fieldErrors.category_id) {
        setFormError(
          error instanceof ApiError && error.status === 409
            ? null
            : getErrorMessage(error, '예산을 설정하지 못했습니다. 다시 시도해 주세요.'),
        );
      }
      focusFirstInvalid(formRef.current);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="card" aria-labelledby="budget-form-heading">
      <h2 id="budget-form-heading" className="card__title">
        예산 설정
      </h2>
      {formError && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {formError}
        </p>
      )}
      <form ref={formRef} className="form form--inline" onSubmit={handleSubmit} noValidate>
        <Field label="대상" error={targetError}>
          {(control) => (
            <select
              {...control}
              name="category_id"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              disabled={submitting}
            >
              <option value={ALL_EXPENSE}>전체 지출</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="금액 (원)" required error={amountError} hint="1원 이상">
          {(control) => (
            <input
              {...control}
              type="text"
              name="amount"
              inputMode="numeric"
              autoComplete="off"
              value={amountText}
              onChange={(e) => setAmountText(formatAmountInput(e.target.value))}
              disabled={submitting}
            />
          )}
        </Field>
        <div className="form__actions">
          <Button type="submit" disabled={submitting} aria-busy={submitting}>
            {submitting ? '설정 중...' : '예산 설정'}
          </Button>
        </div>
      </form>
    </section>
  );
}

function BudgetAmountDialog({
  budget,
  onClose,
  onSave,
}: {
  budget: Budget;
  onClose: () => void;
  onSave: (amount: number) => Promise<void>;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [amountText, setAmountText] = useState(formatAmountInput(String(budget.amount)));
  const [amountError, setAmountError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const amount = parseAmountInput(amountText);
    const error = Number.isNaN(amount) ? '금액은 숫자로 입력해 주세요.' : validateAmount(amount);
    setAmountError(error);
    if (error || amount === null) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setSubmitting(true);
    try {
      await onSave(amount);
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      if (fieldErrors.amount) setAmountError(fieldErrors.amount);
      else setFormError(getErrorMessage(err, '저장하지 못했습니다. 다시 시도해 주세요.'));
      setSubmitting(false);
      focusFirstInvalid(formRef.current);
    }
  };

  return (
    <Modal open title="예산 금액 수정" description={`${budgetTargetName(budget)} 예산의 금액을 바꿉니다.`} onClose={onClose}>
      {formError && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {formError}
        </p>
      )}
      <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate>
        <Field label="금액 (원)" required error={amountError}>
          {(control) => (
            <input
              {...control}
              type="text"
              name="amount"
              inputMode="numeric"
              autoComplete="off"
              value={amountText}
              onChange={(e) => setAmountText(formatAmountInput(e.target.value))}
              disabled={submitting}
            />
          )}
        </Field>
        <div className="form__actions">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            취소
          </Button>
          <Button type="submit" disabled={submitting} aria-busy={submitting}>
            {submitting ? '저장 중...' : '저장'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
