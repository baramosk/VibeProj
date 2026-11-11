import { useRef, useState, type FormEvent } from 'react';
import { getErrorMessage, getFieldErrors } from '../api/client';
import type { Category, CategoryType } from '../api/types';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Field, RadioGroup } from '../components/ui/Field';
import { Modal } from '../components/ui/Modal';
import { useCategoryManager } from '../hooks/useCategories';
import { usePageTitle } from '../hooks/usePageTitle';
import { focusFirstInvalid } from '../lib/focus';
import { CATEGORY_NAME_MAX, validateCategoryName } from '../lib/validation';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews';

/** 카테고리 색상 팔레트 (FR-07). 색만으로 구분하지 않도록 이름을 함께 붙입니다. */
const CATEGORY_COLORS: { value: string; label: string }[] = [
  { value: '#ef4444', label: '빨강' },
  { value: '#f97316', label: '주황' },
  { value: '#eab308', label: '노랑' },
  { value: '#22c55e', label: '초록' },
  { value: '#3b82f6', label: '파랑' },
  { value: '#8b5cf6', label: '보라' },
  { value: '#ec4899', label: '분홍' },
  { value: '#6b7280', label: '회색' },
];

const TYPE_OPTIONS: { value: CategoryType; label: string }[] = [
  { value: 'EXPENSE', label: '지출' },
  { value: 'INCOME', label: '수입' },
];

const SECTION_TITLE: Record<CategoryType, string> = {
  EXPENSE: '지출 카테고리',
  INCOME: '수입 카테고리',
};

function ColorOption({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="swatch-option__chip" style={{ backgroundColor: value }} aria-hidden="true" />
      {label}
    </>
  );
}

export function CategoriesPage() {
  usePageTitle('카테고리');
  const manager = useCategoryManager();
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState<Category | null>(null);
  const [deleting, setDeleting] = useState<Category | null>(null);

  const expense = manager.categories.filter((c) => c.type === 'EXPENSE');
  const income = manager.categories.filter((c) => c.type === 'INCOME');

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>카테고리</h1>
          <p className="page__description">거래를 나눌 분류를 관리합니다. 기본 카테고리도 이름과 색을 바꾸거나 삭제할 수 있습니다.</p>
        </div>
      </header>

      {notice && <Alert variant="success">{notice}</Alert>}

      <CategoryCreateForm
        onCreate={async (input) => {
          await manager.create(input);
          setNotice(`"${input.name.trim()}" 카테고리를 추가했습니다.`);
        }}
      />

      {manager.loading && manager.categories.length === 0 && <LoadingState message="카테고리를 불러오는 중입니다." />}
      {Boolean(manager.error) && manager.categories.length === 0 && (
        <ErrorState
          message={getErrorMessage(manager.error, '카테고리를 불러오지 못했습니다.')}
          onRetry={manager.reload}
        />
      )}

      {!manager.loading && !manager.error && manager.categories.length === 0 && (
        <EmptyState title="카테고리가 없습니다." description="위 양식으로 카테고리를 추가해 보세요." />
      )}

      {(['EXPENSE', 'INCOME'] as const).map((type) => {
        const list = type === 'EXPENSE' ? expense : income;
        if (list.length === 0) return null;
        const headingId = `cat-${type.toLowerCase()}-heading`;
        return (
          <section key={type} className="card" aria-labelledby={headingId}>
            <h2 id={headingId} className="card__title">
              {SECTION_TITLE[type]} ({list.length})
            </h2>
            <ul className="category-list">
              {list.map((category) => (
                <li key={category.id}>
                  <span className="category-list__name">
                    <span
                      className="swatch"
                      style={{ backgroundColor: category.color }}
                      aria-hidden="true"
                    />
                    {category.name}
                    {category.is_default && <span className="badge badge--neutral">기본</span>}
                  </span>
                  <div className="category-list__actions">
                    <Button
                      variant="secondary"
                      aria-label={`${category.name} 카테고리 수정`}
                      onClick={() => setEditing(category)}
                    >
                      수정
                    </Button>
                    <Button
                      variant="danger"
                      aria-label={`${category.name} 카테고리 삭제`}
                      onClick={() => setDeleting(category)}
                    >
                      삭제
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      {editing && (
        <CategoryEditDialog
          category={editing}
          onClose={() => setEditing(null)}
          onSave={async (input) => {
            await manager.update(editing.id, input);
            setEditing(null);
            setNotice(`"${input.name ?? editing.name}" 카테고리를 저장했습니다.`);
          }}
        />
      )}

      {deleting && (
        <CategoryDeleteDialog
          category={deleting}
          candidates={manager.categories.filter((c) => c.type === deleting.type && c.id !== deleting.id)}
          onClose={() => setDeleting(null)}
          onConfirm={async (replacementId) => {
            await manager.remove(deleting.id, replacementId);
            const name = deleting.name;
            setDeleting(null);
            setNotice(`"${name}" 카테고리를 삭제하고 거래를 옮겼습니다.`);
          }}
        />
      )}
    </div>
  );
}

function CategoryCreateForm({
  onCreate,
}: {
  onCreate: (input: { name: string; type: CategoryType; color: string }) => Promise<void>;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [name, setName] = useState('');
  const [type, setType] = useState<CategoryType>('EXPENSE');
  const [color, setColor] = useState(CATEGORY_COLORS[4]?.value ?? '#3b82f6');
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const error = validateCategoryName(name);
    setNameError(error);
    if (error) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setSubmitting(true);
    try {
      await onCreate({ name: name.trim(), type, color });
      setName('');
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      if (fieldErrors.name) setNameError(fieldErrors.name);
      setFormError(getErrorMessage(err, '카테고리를 추가하지 못했습니다.'));
      focusFirstInvalid(formRef.current);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="card" aria-labelledby="cat-create-heading">
      <h2 id="cat-create-heading" className="card__title">
        카테고리 추가
      </h2>
      {formError && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {formError}
        </p>
      )}
      <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate>
        <div className="form--inline">
          <Field label="이름" required error={nameError} hint={`1~${CATEGORY_NAME_MAX}자, 같은 유형 안에서 중복할 수 없습니다.`}>
            {(control) => (
              <input
                {...control}
                type="text"
                name="name"
                maxLength={CATEGORY_NAME_MAX + 10}
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <RadioGroup<CategoryType>
            name="cat-type"
            legend="유형"
            value={type}
            options={TYPE_OPTIONS}
            onChange={setType}
            disabled={submitting}
          />
          <div className="form__actions">
            <Button type="submit" disabled={submitting} aria-busy={submitting}>
              {submitting ? '추가 중...' : '추가'}
            </Button>
          </div>
        </div>
        <RadioGroup<string>
          name="cat-color"
          legend="색상 (선택)"
          value={color}
          options={CATEGORY_COLORS}
          onChange={setColor}
          disabled={submitting}
          className="swatch-group"
          renderOption={(option) => <ColorOption label={option.label} value={option.value} />}
        />
      </form>
    </section>
  );
}

function CategoryEditDialog({
  category,
  onClose,
  onSave,
}: {
  category: Category;
  onClose: () => void;
  onSave: (input: { name: string; color: string }) => Promise<void>;
}) {
  const formRef = useRef<HTMLFormElement>(null);
  const [name, setName] = useState(category.name);
  const [color, setColor] = useState(category.color);
  const [nameError, setNameError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const error = validateCategoryName(name);
    setNameError(error);
    if (error) {
      focusFirstInvalid(formRef.current);
      return;
    }
    setSubmitting(true);
    try {
      await onSave({ name: name.trim(), color });
    } catch (err) {
      const fieldErrors = getFieldErrors(err);
      if (fieldErrors.name) setNameError(fieldErrors.name);
      setFormError(getErrorMessage(err, '저장하지 못했습니다. 다시 시도해 주세요.'));
      setSubmitting(false);
      focusFirstInvalid(formRef.current);
    }
  };

  return (
    <Modal open title="카테고리 수정" description={`${SECTION_TITLE[category.type]} 중 "${category.name}"을(를) 고칩니다.`} onClose={onClose}>
      {formError && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {formError}
        </p>
      )}
      <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate>
        <Field label="이름" required error={nameError}>
          {(control) => (
            <input
              {...control}
              type="text"
              name="name"
              maxLength={CATEGORY_NAME_MAX + 10}
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
            />
          )}
        </Field>
        <RadioGroup<string>
          name="edit-color"
          legend="색상"
          value={color}
          options={CATEGORY_COLORS}
          onChange={setColor}
          disabled={submitting}
          className="swatch-group"
          renderOption={(option) => <ColorOption label={option.label} value={option.value} />}
        />
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

function CategoryDeleteDialog({
  category,
  candidates,
  onClose,
  onConfirm,
}: {
  category: Category;
  candidates: Category[];
  onClose: () => void;
  onConfirm: (replacementId: number) => Promise<void>;
}) {
  const [replacement, setReplacement] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [replacementError, setReplacementError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!replacement) {
      setReplacementError('거래를 옮길 카테고리를 선택해 주세요.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(Number(replacement));
    } catch (err) {
      setError(getErrorMessage(err, '삭제하지 못했습니다. 다시 시도해 주세요.'));
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      title="카테고리를 삭제할까요?"
      description={`"${category.name}" 카테고리의 거래는 아래에서 고른 카테고리로 옮겨지고, 이 카테고리의 예산은 삭제됩니다.`}
      onClose={onClose}
    >
      {candidates.length === 0 ? (
        <Alert variant="warning">
          같은 유형의 다른 카테고리가 없습니다. 거래를 옮길 카테고리를 먼저 추가해 주세요.
        </Alert>
      ) : (
        <Field label="거래를 옮길 카테고리" required error={replacementError}>
          {(control) => (
            <select
              {...control}
              name="replacement"
              value={replacement}
              onChange={(e) => {
                setReplacement(e.target.value);
                setReplacementError(null);
              }}
              disabled={busy}
            >
              <option value="">선택하세요</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
        </Field>
      )}
      {error && (
        <p className="form-error" role="alert">
          <span aria-hidden="true">! </span>
          {error}
        </p>
      )}
      <div className="modal__actions">
        <Button variant="secondary" onClick={onClose} disabled={busy}>
          취소
        </Button>
        <Button
          variant="danger"
          onClick={handleConfirm}
          disabled={busy || candidates.length === 0}
          aria-busy={busy}
        >
          {busy ? '삭제 중...' : '삭제'}
        </Button>
      </div>
    </Modal>
  );
}
