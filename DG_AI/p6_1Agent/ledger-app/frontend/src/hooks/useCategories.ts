import { categoryApi } from '../api/endpoints';
import type { Category, CategoryType } from '../api/types';
import { useAsync } from './useAsync';

/** 카테고리 목록 (읽기 전용). 거래 입력 폼 등에서 씁니다. */
export function useCategoryList(type?: CategoryType) {
  return useAsync<Category[]>((signal) => categoryApi.list(type, signal), [type]);
}

/** 카테고리 관리 화면용: 전체 목록과 추가, 수정, 삭제. 변경 후 목록을 다시 불러옵니다. */
export function useCategoryManager() {
  const list = useAsync<Category[]>((signal) => categoryApi.list(undefined, signal), []);

  const create = async (input: { name: string; type: CategoryType; color: string }) => {
    const created = await categoryApi.create(input);
    list.reload();
    return created;
  };

  const update = async (id: number, input: { name?: string; color?: string }) => {
    const updated = await categoryApi.update(id, input);
    list.reload();
    return updated;
  };

  const remove = async (id: number, replacementId: number) => {
    await categoryApi.remove(id, replacementId);
    list.reload();
  };

  return {
    categories: list.data ?? [],
    loading: list.loading,
    error: list.error,
    reload: list.reload,
    create,
    update,
    remove,
  };
}
