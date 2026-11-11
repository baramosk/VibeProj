import { useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { getErrorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { ConfirmDialog } from '../components/ui/Modal';
import { usePageTitle } from '../hooks/usePageTitle';
import { formatDateTimeLabel } from '../lib/date';
import { focusFirstInvalid } from '../lib/focus';

export function SettingsPage() {
  usePageTitle('설정');
  const { user, deleteAccount } = useAuth();
  const navigate = useNavigate();
  const formRef = useRef<HTMLFormElement>(null);

  const [password, setPassword] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const handleRequestDelete = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const nextPasswordError = password === '' ? '비밀번호를 입력해 주세요.' : null;
    setPasswordError(nextPasswordError);
    if (nextPasswordError || !confirmed) {
      if (!confirmed) setFormError('탈퇴 확인에 체크해 주세요.');
      focusFirstInvalid(formRef.current);
      return;
    }
    setDialogError(null);
    setDialogOpen(true);
  };

  const handleDelete = async () => {
    setBusy(true);
    setDialogError(null);
    try {
      await deleteAccount(password);
      navigate('/login', { replace: true, state: { notice: '회원 탈퇴가 완료되었습니다. 모든 데이터가 삭제되었습니다.' } });
    } catch (error) {
      setDialogError(getErrorMessage(error, '탈퇴하지 못했습니다. 비밀번호를 확인한 뒤 다시 시도해 주세요.'));
      setBusy(false);
    }
  };

  if (!user) return null;

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>설정</h1>
          <p className="page__description">계정 정보를 확인하고 탈퇴할 수 있습니다.</p>
        </div>
      </header>

      <section className="card" aria-labelledby="account-heading">
        <h2 id="account-heading" className="card__title">
          계정 정보
        </h2>
        <dl className="definition">
          <dt>닉네임</dt>
          <dd>{user.nickname}</dd>
          <dt>이메일</dt>
          <dd>{user.email}</dd>
          <dt>가입일</dt>
          <dd>
            <time dateTime={user.created_at}>{formatDateTimeLabel(user.created_at)}</time>
          </dd>
        </dl>
      </section>

      <section className="card danger-zone" aria-labelledby="delete-heading">
        <h2 id="delete-heading" className="card__title">
          회원 탈퇴
        </h2>
        <p className="text-muted">
          탈퇴하면 계정과 모든 거래, 카테고리, 예산, 알림이 즉시 삭제됩니다. 삭제한 데이터는 복구할 수 없습니다.
        </p>
        {formError && (
          <p className="form-error" role="alert">
            <span aria-hidden="true">! </span>
            {formError}
          </p>
        )}
        <form ref={formRef} className="form" onSubmit={handleRequestDelete} noValidate>
          <Field label="비밀번호 확인" required error={passwordError}>
            {(control) => (
              <input
                {...control}
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            )}
          </Field>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="confirm"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>모든 데이터가 삭제되며 복구할 수 없다는 것을 이해했습니다.</span>
          </label>
          <div className="form__actions">
            <Button type="submit" variant="danger">
              회원 탈퇴
            </Button>
          </div>
        </form>
      </section>

      {/* 최종 확인 창. 비밀번호는 서버에서 다시 검증합니다. */}
      <ConfirmDialog
        open={dialogOpen}
        title="정말 탈퇴할까요?"
        message="이 작업은 되돌릴 수 없습니다. 확인을 누르면 계정과 모든 데이터가 바로 삭제됩니다."
        confirmLabel="탈퇴하기"
        danger
        busy={busy}
        error={dialogError}
        onConfirm={handleDelete}
        onCancel={() => setDialogOpen(false)}
      />
    </div>
  );
}
