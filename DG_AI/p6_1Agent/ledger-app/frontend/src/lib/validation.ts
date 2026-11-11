/**
 * 화면 입력 검증 (클라이언트 1차 검증).
 * 서버가 같은 규칙으로 다시 검증하므로 (NFR-06), 여기서는 사용자 안내 목적입니다.
 * 각 함수는 문제가 없으면 null, 있으면 사용자에게 보여줄 문장을 돌려줍니다.
 */

export const CATEGORY_NAME_MAX = 20;
export const NICKNAME_MAX = 20;
export const MEMO_MAX = 200;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | null {
  const value = email.trim();
  if (value === '') return '이메일을 입력해 주세요.';
  if (!EMAIL_PATTERN.test(value)) return '이메일 형식이 올바르지 않습니다.';
  return null;
}

/** FR-01: 8자 이상, 영문과 숫자 포함 (권장안). */
export function validatePassword(password: string): string | null {
  if (password === '') return '비밀번호를 입력해 주세요.';
  if (password.length < 8) return '비밀번호는 8자 이상이어야 합니다.';
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    return '비밀번호에는 영문과 숫자가 모두 포함되어야 합니다.';
  }
  return null;
}

export function validatePasswordConfirm(password: string, confirm: string): string | null {
  if (confirm === '') return '비밀번호 확인을 입력해 주세요.';
  if (password !== confirm) return '비밀번호가 일치하지 않습니다.';
  return null;
}

export function validateNickname(nickname: string): string | null {
  const value = nickname.trim();
  if (value === '') return '닉네임을 입력해 주세요.';
  if (value.length > NICKNAME_MAX) return `닉네임은 ${NICKNAME_MAX}자 이하여야 합니다.`;
  return null;
}

/** FR-07: 이름 1~20자, 공백 제거 후 검사. */
export function validateCategoryName(name: string): string | null {
  const value = name.trim();
  if (value === '') return '카테고리 이름을 입력해 주세요.';
  if (value.length > CATEGORY_NAME_MAX) return `카테고리 이름은 ${CATEGORY_NAME_MAX}자 이하여야 합니다.`;
  return null;
}

/** FR-10: 메모 최대 200자 (선택 항목). */
export function validateMemo(memo: string): string | null {
  if (memo.length > MEMO_MAX) return `메모는 ${MEMO_MAX}자 이하여야 합니다.`;
  return null;
}
