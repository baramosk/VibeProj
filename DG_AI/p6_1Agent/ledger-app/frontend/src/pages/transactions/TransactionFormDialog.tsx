import { useRef, useState, type FormEvent } from 'react';
import { getErrorMessage, getFieldErrors } from '../../api/client';
import type { Category, CategoryType, Transaction, TransactionInput } from '../../api/types';
import { Button } from '../../components/ui/Button';
import { Field, RadioGroup } from '../../components/ui/Field';
import { Modal } from '../../components/ui/Modal';
import { focusFirstInvalid } from '../../lib/focus';
import { isFutureDate, isValidDate, todayKST } from '../../lib/date';
import { formatAmountInput, parseAmountInput, validateAmount } from '../../lib/money';
import { MEMO_MAX, validateMemo } from '../../lib/validation';

type FieldName = 'type' | 'amount' | 'category' | 'date' | 'memo';
type FieldErrors = Partial<Record<FieldName, string>>;

/** 서버 details 키 -> 화면 필드 이름 */
const SERVER_FIELD_MAP: Record<string, FieldName> = {
  type: 'type',
  amount: 'amount',
  category_id: 'category',
  occurred_on: 'date',
  memo: 'memo',
};

const TYPE_OPTIONS: { value: CategoryType; label: string }[] = [
  { value: 'EXPENSE', label: '지출' },
  { value: 'INCOME', label: '수입' },
];

interface TransactionFormDialogProps {
  open: boolean;
  mode: 'create' | 'edit';
  initial: Transaction | null;
  categories: Category[];
  onClose: () => void;
  onSubmit: (input: TransactionInput) => Promise<void>;
}

/**
 * 거래 기록과 수정 대화 상자 (FR-10, FR-12).
 * 모든 값은 서버에서 다시 검증합니다. 여기서는 입력 중 안내와 오류 표시만 합니다.
 */
export function TransactionFormDialog({
  open,
  mode,
  initial,
  categories,
  onClose,
  onSubmit,
}: TransactionFormDialogProps) {
  // 대화 상자가 열릴 때마다 입력 상태를 새로 만듭니다 (부모가 key로 다시 마운트합니다).
  return (
    <Modal
      open={open}
      title={mode === 'create' ? '거래 기록' : '거래 수정'}
      description={mode === 'create' ? '수입이나 지출을 기록합니다.' : '잘못 입력한 내용을 고칩니다.'}
      onClose={onClose}
    >
      <TransactionForm
        key={initial?.id ?? 'new'}
        mode={mode}
        initial={initial}
        categories={categories}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function TransactionForm({
  mode,
  initial,
  categories,
  onClose,
  onSubmit,
}: Omit<TransactionFormDialogProps, 'open'>) {
  const formRef = useRef<HTMLFormElement>(null);
  const [type, setType] = useState<CategoryType>(initial?.type ?? 'EXPENSE');
  const [amountText, setAmountText] = useState(initial ? formatAmountInput(String(initial.amount)) : '');
  const [categoryId, setCategoryId] = useState<string>(initial ? String(initial.category_id) : '');
  const [date, setDate] = useState(initial?.occurred_on ?? todayKST());
  const [memo, setMemo] = useState(initial?.memo ?? '');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const categoryOptions = categories.filter((c) => c.type === type);

  const handleTypeChange = (next: CategoryType) => {
    setType(next);
    // 유형이 바뀌면 이전 유형의 카테고리는 선택 해제합니다.
    if (categoryId && !categories.some((c) => String(c.id) === categoryId && c.type === next)) {
      setCategoryId('');
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    const amount = parseAmountInput(amountText);
    const nextErrors: FieldErrors = {};
    const amountError = Number.isNaN(amount) ? '금액은 숫자로 입력해 주세요.' : validateAmount(amount);
    if (amountError) nextErrors.amount = amountError;
    if (!categoryId) nextErrors.category = '카테고리를 선택해 주세요.';
    if (!isValidDate(date)) nextErrors.date = '날짜를 올바르게 입력해 주세요.';
    else if (isFutureDate(date)) nextErrors.date = '미래 날짜는 입력할 수 없습니다.';
    const memoError = validateMemo(memo);
    if (memoError) nextErrors.memo = memoError;

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0 || amount === null || Number.isNaN(amount)) {
      focusFirstInvalid(formRef.current);
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        type,
        amount,
        category_id: Number(categoryId),
        occurred_on: date,
        memo: memo.trim() === '' ? null : memo.trim(),
      });
    } catch (error) {
      const serverErrors: FieldErrors = {};
      for (const [key, message] of Object.entries(getFieldErrors(error))) {
        const field = SERVER_FIELD_MAP[key];
        if (field) serverErrors[field] = message;
      }
      setErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) {
        setFormError(getErrorMessage(error, '저장하지 못했습니다. 잠시 후 다시 시도해 주세요.'));
      }
      setSubmitting(false);
      focusFirstInvalid(formRef.current);
    }
  };

  return (
    <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate aria-label={mode === 'create' ? '거래 기록 폼' : '거래 수정 폼'}>
      {formError && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {formError}
        </p>
      )}

      <RadioGroup<CategoryType>
        name="tx-type"
        legend="유형"
        value={type}
        options={TYPE_OPTIONS}
        onChange={handleTypeChange}
        disabled={submitting}
      />
      {errors.type && <p className="field__error">{errors.type}</p>}

      <Field label="금액 (원)" required error={errors.amount} hint="숫자만 입력합니다. 예: 12000">
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

      <Field label="카테고리" required error={errors.category}>
        {(control) => (
          <select
            {...control}
            name="category_id"
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            disabled={submitting}
          >
            <option value="">선택하세요</option>
            {categoryOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </Field>

      <Field label="날짜" required error={errors.date}>
        {(control) => (
          <input
            {...control}
            type="date"
            name="occurred_on"
            value={date}
            max={todayKST()}
            onChange={(e) => setDate(e.target.value)}
            disabled={submitting}
          />
        )}
      </Field>

      <Field label="메모 (선택)" error={errors.memo}>
        {(control) => (
          <>
            <textarea
              {...control}
              name="memo"
              maxLength={MEMO_MAX}
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
              disabled={submitting}
              aria-describedby={[control['aria-describedby'], `${control.id}-count`].filter(Boolean).join(' ')}
            />
            <span id={`${control.id}-count`} className="field__count">
              {memo.length} / {MEMO_MAX}자
            </span>
          </>
        )}
      </Field>

      <div className="form__actions">
        <Button variant="secondary" onClick={onClose} disabled={submitting}>
          취소
        </Button>
        <Button type="submit" disabled={submitting} aria-busy={submitting}>
          {submitting ? '저장 중...' : mode === 'create' ? '기록하기' : '수정 저장'}
        </Button>
      </div>
    </form>
  );
}
