import { useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation } from 'react-router';
import { useAuth } from '../auth/AuthContext';
import { ApiError, getErrorMessage } from '../api/client';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { usePageTitle } from '../hooks/usePageTitle';
import { focusFirstInvalid } from '../lib/focus';
import { validateEmail } from '../lib/validation';

/** FR-02: 계정 존재 여부를 드러내지 않도록 실패 문구는 고정합니다. */
const LOGIN_FAILED_MESSAGE = '이메일 또는 비밀번호가 올바르지 않습니다.';

export function LoginPage() {
  usePageTitle('로그인');
  const { user, login } = useAuth();
  const location = useLocation();
  const notice = (location.state as { notice?: string } | null)?.notice;

  const formRef = useRef<HTMLFormElement>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const nextEmailError = validateEmail(email);
    const nextPasswordError = password === '' ? '비밀번호를 입력해 주세요.' : null;
    setEmailError(nextEmailError);
    setPasswordError(nextPasswordError);
    if (nextEmailError || nextPasswordError) {
      focusFirstInvalid(formRef.current);
      return;
    }

    setSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError(LOGIN_FAILED_MESSAGE);
      } else {
        setFormError(getErrorMessage(error, '로그인하지 못했습니다. 잠시 후 다시 시도해 주세요.'));
      }
      setSubmitting(false);
      focusFirstInvalid(formRef.current);
      return;
    }
    setSubmitting(false);
  };

  return (
    <main className="auth-page">
      <p className="auth-page__brand">가계부</p>
      <div className="auth">
        <h1 className="auth__title">로그인</h1>
        {notice && <Alert variant="success">{notice}</Alert>}
        {formError && <Alert variant="error">{formError}</Alert>}
        <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate>
          <Field label="이메일" required error={emailError}>
            {(control) => (
              <input
                {...control}
                type="email"
                name="email"
                autoComplete="email"
                inputMode="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <Field label="비밀번호" required error={passwordError}>
            {(control) => (
              <input
                {...control}
                type="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <Button type="submit" block disabled={submitting} aria-busy={submitting}>
            {submitting ? '로그인 중...' : '로그인'}
          </Button>
        </form>
        <p className="auth__footer">
          아직 계정이 없나요? <Link to="/signup">회원가입</Link>
        </p>
      </div>
    </main>
  );
}
