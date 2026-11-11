import { transactionApi } from '../api/endpoints';
import type { TransactionFilters, TransactionInput } from '../api/types';
import { useAsync } from './useAsync';

/** 거래 목록 조회와 기록, 수정, 삭제. 변경 후 현재 조건으로 다시 불러옵니다 (FR-10~13). */
export function useTransactionManager(filters: TransactionFilters) {
  const list = useAsync(
    (signal) => transactionApi.list(filters, signal),
    [filters.from, filters.to, filters.type, filters.category_id, filters.page, filters.size],
  );

  const create = async (input: TransactionInput) => {
    const res = await transactionApi.create(input);
    list.reload();
    return res;
  };

  const update = async (id: number, input: Partial<TransactionInput>) => {
    const res = await transactionApi.update(id, input);
    list.reload();
    return res;
  };

  const remove = async (id: number) => {
    const res = await transactionApi.remove(id);
    list.reload();
    return res;
  };

  return {
    result: list.data,
    loading: list.loading,
    error: list.error,
    reload: list.reload,
    create,
    update,
    remove,
  };
}
