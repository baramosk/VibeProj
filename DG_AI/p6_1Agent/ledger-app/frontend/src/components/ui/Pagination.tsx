import { Button } from './Button';

interface PaginationProps {
  page: number;
  size: number;
  total: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}

export function Pagination({ page, size, total, onPageChange, disabled = false }: PaginationProps) {
  const lastPage = Math.max(1, Math.ceil(total / size));
  return (
    <nav className="pagination" aria-label="거래 목록 페이지">
      <Button variant="secondary" onClick={() => onPageChange(page - 1)} disabled={disabled || page <= 1}>
        이전 페이지
      </Button>
      <span className="pagination__status" aria-live="polite">
        {page} / {lastPage} 페이지
      </span>
      <Button variant="secondary" onClick={() => onPageChange(page + 1)} disabled={disabled || page >= lastPage}>
        다음 페이지
      </Button>
    </nav>
  );
}
