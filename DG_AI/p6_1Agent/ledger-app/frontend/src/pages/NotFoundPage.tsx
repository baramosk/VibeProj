import { Link } from 'react-router';
import { usePageTitle } from '../hooks/usePageTitle';

export function NotFoundPage() {
  usePageTitle('페이지를 찾을 수 없음');
  return (
    <main className="auth-page">
      <div className="auth">
        <h1 className="auth__title">페이지를 찾을 수 없습니다</h1>
        <p className="text-muted">주소가 바르게 입력되었는지 확인해 주세요.</p>
        <Link to="/dashboard" className="btn btn--primary">
          대시보드로 이동
        </Link>
      </div>
    </main>
  );
}
