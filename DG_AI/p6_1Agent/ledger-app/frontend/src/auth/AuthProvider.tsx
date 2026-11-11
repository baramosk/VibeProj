import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { ApiError, setCsrfToken, setUnauthorizedHandler } from '../api/client';
import { authApi } from '../api/endpoints';
import type { User } from '../api/types';
import { AuthContext, type AuthContextValue } from './AuthContext';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);

  const clearSession = useCallback(() => {
    setCsrfToken(null);
    setUser(null);
  }, []);

  // 세션 확인: 새로고침 후에도 로그인 상태를 복원합니다.
  // 백엔드가 없거나 세션이 없으면 로그인 상태가 아닌 것으로 봅니다.
  useEffect(() => {
    const controller = new AbortController();
    authApi
      .me(controller.signal)
      .then((res) => {
        setCsrfToken(res.csrf_token);
        setUser(res.user);
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        clearSession();
      })
      .finally(() => {
        if (!controller.signal.aborted) setChecking(false);
      });
    return () => controller.abort();
  }, [clearSession]);

  // 세션 만료(401)가 감지되면 로그인 상태를 해제합니다.
  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await authApi.login({ email, password });
    setCsrfToken(res.csrf_token);
    setUser(res.user);
  }, []);

  const signup = useCallback(async (input: { email: string; password: string; nickname: string }) => {
    const res = await authApi.signup(input);
    setCsrfToken(res.csrf_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      // 서버 응답이 실패해도 화면의 로그인 상태는 해제합니다.
      if (!(error instanceof ApiError)) throw error;
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const deleteAccount = useCallback(
    async (password: string) => {
      await authApi.deleteAccount(password);
      clearSession();
    },
    [clearSession],
  );

  const value = useMemo<AuthContextValue>(
    () => ({ user, checking, login, signup, logout, deleteAccount }),
    [user, checking, login, signup, logout, deleteAccount],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
