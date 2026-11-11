import { budgetApi } from '../api/endpoints';
import type { Budget } from '../api/types';
import { useAsync } from './useAsync';

/**
 * 월별 예산 목록과 설정 (FR-18, FR-19).
 * 같은 대상과 월의 예산이 이미 있으면 create는 409 ApiError를 던집니다.
 * 화면은 그 경우 overwriteBudget으로 금액을 덮어쓸지 사용자에게 확인합니다.
 */
export function useBudgetManager(yearMonth: string) {
  const list = useAsync<Budget[]>((signal) => budgetApi.list(yearMonth, signal), [yearMonth]);

  const create = async (input: { amount: number; category_id?: number }) => {
    const created = await budgetApi.create({ year_month: yearMonth, ...input });
    list.reload();
    return created;
  };

  /** 같은 대상의 기존 예산 금액을 바꿉니다. 대상을 찾지 못하면 false. */
  const overwriteBudget = async (categoryId: number | null, amount: number): Promise<boolean> => {
    const target = (list.data ?? []).find((b) => (b.category_id ?? null) === categoryId);
    if (!target) {
      list.reload();
      return false;
    }
    await budgetApi.updateAmount(target.id, amount);
    list.reload();
    return true;
  };

  const updateAmount = async (id: number, amount: number) => {
    const updated = await budgetApi.updateAmount(id, amount);
    list.reload();
    return updated;
  };

  const remove = async (id: number) => {
    await budgetApi.remove(id);
    list.reload();
  };

  return {
    budgets: list.data ?? [],
    loading: list.loading,
    error: list.error,
    reload: list.reload,
    create,
    overwriteBudget,
    updateAmount,
    remove,
  };
}
