import type { ReactNode } from 'react';

export type AlertVariant = 'error' | 'success' | 'info' | 'warning';

const ICONS: Record<AlertVariant, string> = { error: '!', success: '✓', info: 'i', warning: '!' };
const LABELS: Record<AlertVariant, string> = { error: '오류', success: '완료', info: '안내', warning: '주의' };

/**
 * 상태 메시지. 오류는 role="alert"로 바로 읽히고, 그 밖은 role="status"로 읽힙니다.
 * 색상과 함께 아이콘과 머리말을 표시해 색에만 의존하지 않습니다 (NFR-17).
 */
export function Alert({ variant = 'info', children }: { variant?: AlertVariant; children: ReactNode }) {
  return (
    <div role={variant === 'error' ? 'alert' : 'status'} className={`alert alert--${variant}`}>
      <span className="alert__icon" aria-hidden="true">
        {ICONS[variant]}
      </span>
      <div className="alert__body">
        <span className="sr-only">{LABELS[variant]}: </span>
        {children}
      </div>
    </div>
  );
}
