import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { useAuth } from '../../auth/AuthContext';
import { LoadingState } from '../ui/StateViews';

/** 로그인하지 않은 사용자는 로그인 화면으로 보냅니다 (FR-03). */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, checking } = useAuth();
  const location = useLocation();

  if (checking) {
    return (
      <div className="page-center">
        <LoadingState message="로그인 상태를 확인하는 중입니다." />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
