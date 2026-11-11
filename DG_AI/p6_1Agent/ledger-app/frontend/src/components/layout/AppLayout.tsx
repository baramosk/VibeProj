import { useEffect, useRef } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router';
import { useAuth } from '../../auth/AuthContext';
import { useUnreadNotificationCount } from '../../hooks/useNotifications';
import { Button } from '../ui/Button';

const NAV_ITEMS = [
  { to: '/dashboard', label: '대시보드' },
  { to: '/transactions', label: '거래' },
  { to: '/budgets', label: '예산' },
  { to: '/categories', label: '카테고리' },
  { to: '/settings', label: '설정' },
] as const;

/** 로그인 후 공통 화면 틀: 건너뛰기 링크, 헤더, 주요 메뉴, 본문. */
export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const mainRef = useRef<HTMLElement>(null);
  const { unreadCount } = useUnreadNotificationCount(location.pathname);

  // 화면이 바뀌면 본문 제목으로 포커스를 옮겨 키보드 사용자가 새 화면을 바로 알 수 있게 합니다.
  useEffect(() => {
    if (location.key !== 'default') mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname, location.key]);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>
      <header className="app-header">
        <div className="app-header__top">
          <NavLink to="/dashboard" className="brand">
            가계부
          </NavLink>
          <div className="app-header__actions">
            <NavLink to="/notifications" className="header-link">
              알림
              {unreadCount > 0 && (
                <span className="count-badge">
                  <span className="sr-only">읽지 않은 알림 </span>
                  {unreadCount}
                  <span className="sr-only">개</span>
                </span>
              )}
            </NavLink>
            <span className="app-header__user">{user?.nickname}</span>
            <Button variant="ghost" onClick={handleLogout}>
              로그아웃
            </Button>
          </div>
        </div>
        <nav aria-label="주요 메뉴" className="app-nav">
          <ul className="app-nav__list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} className="app-nav__link">
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main-content" ref={mainRef} tabIndex={-1} className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
