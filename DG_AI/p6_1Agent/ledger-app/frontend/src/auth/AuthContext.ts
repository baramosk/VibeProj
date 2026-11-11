import { createContext, useContext } from 'react';
import type { User } from '../api/types';

export interface AuthContextValue {
  user: User | null;
  /** 최초 세션 확인이 끝나기 전에는 true */
  checking: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (input: { email: string; password: string; nickname: string }) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: (password: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth는 AuthProvider 안에서만 쓸 수 있습니다.');
  return value;
}
