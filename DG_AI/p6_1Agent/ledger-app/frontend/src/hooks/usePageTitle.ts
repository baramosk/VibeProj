import { useEffect } from 'react';

const APP_NAME = '가계부';

/** 화면마다 문서 제목을 바꿉니다. 스크린 리더가 화면 전환을 알 수 있게 합니다. */
export function usePageTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} | ${APP_NAME}`;
  }, [title]);
}
