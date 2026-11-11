import { setupServer } from 'msw/node';
import { defaultHandlers } from './handlers';

/** 화면 테스트용 API 모킹 서버 (MSW). 백엔드가 없어도 계약 형태로 응답합니다. */
export const server = setupServer(...defaultHandlers);
