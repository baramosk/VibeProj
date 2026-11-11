import { useState } from 'react';
import { Link } from 'react-router';
import { getErrorMessage } from '../api/client';
import type { AppNotification } from '../api/types';
import { Alert } from '../components/ui/Alert';
import { Button } from '../components/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StateViews';
import { useNotificationManager } from '../hooks/useNotifications';
import { usePageTitle } from '../hooks/usePageTitle';
import { formatDateTimeLabel } from '../lib/date';

export function NotificationsPage() {
  usePageTitle('알림');
  const manager = useNotificationManager();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleMarkAll = async () => {
    setBusy(true);
    setError(null);
    try {
      await manager.markAllRead();
    } catch (err) {
      setError(getErrorMessage(err, '일부 알림을 읽음으로 바꾸지 못했습니다. 다시 시도해 주세요.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1>알림</h1>
          <p className="page__description">
            읽지 않은 알림 {manager.unreadCount}개
          </p>
        </div>
        <Button variant="secondary" onClick={handleMarkAll} disabled={busy || manager.unreadCount === 0}>
          모두 읽음
        </Button>
      </header>

      {error && <Alert variant="error">{error}</Alert>}

      {manager.loading && manager.items.length === 0 && <LoadingState message="알림을 불러오는 중입니다." />}
      {Boolean(manager.error) && manager.items.length === 0 && (
        <ErrorState message={getErrorMessage(manager.error, '알림을 불러오지 못했습니다.')} onRetry={manager.reload} />
      )}

      {!manager.loading && !manager.error && manager.items.length === 0 && (
        <EmptyState
          title="알림이 없습니다."
          description="예산의 80%를 쓰거나 100%를 넘으면 여기에 알림이 생성됩니다."
        />
      )}

      {manager.items.length > 0 && (
        <ul className="notification-list" aria-label="알림 목록">
          {manager.items.map((item) => (
            <NotificationRow
              key={item.id}
              item={item}
              onOpen={() => {
                if (!item.is_read) {
                  manager.markRead(item.id).catch(() => {
                    // 읽음 처리가 실패해도 예산 화면으로 이동은 막지 않습니다. 다음 진입 때 다시 표시됩니다.
                  });
                }
              }}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function NotificationRow({ item, onOpen }: { item: AppNotification; onOpen: () => void }) {
  return (
    <li className={`notification-item${item.is_read ? '' : ' notification-item--unread'}`}>
      <div className="notification-item__meta">
        <span className={`badge ${item.is_read ? 'badge--neutral' : 'badge--warning'}`}>
          <span className="badge__icon" aria-hidden="true">
            {item.is_read ? '✓' : '●'}
          </span>
          {item.is_read ? '읽음' : '읽지 않음'}
        </span>
        <time dateTime={item.created_at}>{formatDateTimeLabel(item.created_at)}</time>
        <span>{item.threshold_percent === 100 ? '초과 알림' : '주의 알림'}</span>
      </div>
      <Link
        className="notification-item__link"
        to={`/budgets?month=${item.year_month}`}
        onClick={onOpen}
      >
        {item.message}
        <span className="sr-only"> (예산 화면으로 이동)</span>
      </Link>
    </li>
  );
}
