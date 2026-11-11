import { useRef, useState, type FormEvent } from 'react';
import { Link, Navigate } from 'react-router';
import { useAuth } from '../auth/AuthContext';
import { getErrorMessage, getFieldErrors, isApiError } from '../api/client';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { Field } from '../components/ui/Field';
import { usePageTitle } from '../hooks/usePageTitle';
import { focusFirstInvalid } from '../lib/focus';
import {
  validateEmail,
  validateNickname,
  validatePassword,
  validatePasswordConfirm,
} from '../lib/validation';

type FieldName = 'email' | 'password' | 'passwordConfirm' | 'nickname';
type FieldErrors = Partial<Record<FieldName, string>>;

/** 서버의 details 키(영문 필드명)를 화면의 필드 이름으로 바꿉니다. */
const SERVER_FIELD_MAP: Record<string, FieldName> = {
  email: 'email',
  password: 'password',
  nickname: 'nickname',
};

export function SignupPage() {
  usePageTitle('회원가입');
  const { user, signup } = useAuth();
  const formRef = useRef<HTMLFormElement>(null);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [nickname, setNickname] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const validateAll = (): FieldErrors => {
    const next: FieldErrors = {};
    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    const confirmError = validatePasswordConfirm(password, passwordConfirm);
    const nicknameError = validateNickname(nickname);
    if (emailError) next.email = emailError;
    if (passwordError) next.password = passwordError;
    if (confirmError) next.passwordConfirm = confirmError;
    if (nicknameError) next.nickname = nicknameError;
    return next;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    const nextErrors = validateAll();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      focusFirstInvalid(formRef.current);
      return;
    }

    setSubmitting(true);
    try {
      await signup({ email: email.trim(), password, nickname: nickname.trim() });
    } catch (error) {
      const serverErrors: FieldErrors = {};
      for (const [key, message] of Object.entries(getFieldErrors(error))) {
        const field = SERVER_FIELD_MAP[key];
        if (field) serverErrors[field] = message;
      }
      // 409는 이메일 중복입니다 (대소문자 무시).
      if (isApiError(error) && error.status === 409 && !serverErrors.email) {
        serverErrors.email = getErrorMessage(error, '이미 가입된 이메일입니다.');
      }
      setErrors(serverErrors);
      if (Object.keys(serverErrors).length === 0) {
        setFormError(getErrorMessage(error, '가입하지 못했습니다. 잠시 후 다시 시도해 주세요.'));
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
        <h1 className="auth__title">회원가입</h1>
        {formError && <Alert variant="error">{formError}</Alert>}
        <form ref={formRef} className="form" onSubmit={handleSubmit} noValidate>
          <Field label="이메일" required error={errors.email} hint="로그인에 사용합니다.">
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
          <Field label="비밀번호" required error={errors.password} hint="8자 이상, 영문과 숫자를 모두 포함해 주세요.">
            {(control) => (
              <input
                {...control}
                type="password"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <Field label="비밀번호 확인" required error={errors.passwordConfirm}>
            {(control) => (
              <input
                {...control}
                type="password"
                name="passwordConfirm"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <Field label="닉네임" required error={errors.nickname} hint="20자 이하">
            {(control) => (
              <input
                {...control}
                type="text"
                name="nickname"
                autoComplete="nickname"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                disabled={submitting}
              />
            )}
          </Field>
          <Button type="submit" block disabled={submitting} aria-busy={submitting}>
            {submitting ? '가입 처리 중...' : '가입하고 시작하기'}
          </Button>
        </form>
        <p className="auth__footer">
          이미 계정이 있나요? <Link to="/login">로그인</Link>
        </p>
      </div>
    </main>
  );
}
