import { useCallback, useEffect, useState } from 'react';

export interface AsyncState<T> {
  data: T | undefined;
  error: unknown;
  /** 최초 로딩 또는 재요청 중 */
  loading: boolean;
  /** 재요청합니다. 기존 데이터는 새 응답이 올 때까지 유지합니다. */
  reload: () => void;
}

function sameDeps(a: readonly unknown[], b: readonly unknown[]): boolean {
  return a.length === b.length && a.every((value, index) => Object.is(value, b[index]));
}

/**
 * 요청 하나를 실행하고 로딩과 오류 상태를 관리합니다.
 * deps가 바뀌거나 reload가 불리면 새 요청을 보내고, 이전 요청은 취소합니다.
 * 로딩 여부는 "요청 키"와 "마지막으로 끝난 요청 키"의 비교로 정하므로
 * 효과 안에서 동기적으로 상태를 바꾸지 않습니다.
 */
export function useAsync<T>(loader: (signal: AbortSignal) => Promise<T>, deps: readonly unknown[]): AsyncState<T> {
  const [reloadCount, setReloadCount] = useState(0);

  // deps가 바뀌었는지 렌더 중에 확인하고, 바뀌었으면 세대(epoch) 번호를 올립니다.
  const [depsState, setDepsState] = useState<{ deps: readonly unknown[]; epoch: number }>({ deps, epoch: 0 });
  let epoch = depsState.epoch;
  if (!sameDeps(depsState.deps, deps)) {
    epoch = depsState.epoch + 1;
    setDepsState({ deps, epoch });
  }

  const requestKey = `${epoch}:${reloadCount}`;
  const [settled, setSettled] = useState<{ key: string; data: T | undefined; error: unknown }>({
    key: '',
    data: undefined,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    loader(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setSettled({ key: requestKey, data, error: null });
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setSettled((prev) => ({ key: requestKey, data: prev.data, error }));
        }
      },
    );
    return () => controller.abort();
    // loader는 매 렌더 새로 만들어지므로 의존성에서 뺍니다. 요청 식별은 requestKey와 deps로 합니다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestKey]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);

  const loading = settled.key !== requestKey;
  return { data: settled.data, error: loading ? null : settled.error, loading, reload };
}
