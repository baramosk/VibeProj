import { describe, expect, it } from 'vitest';
import {
  validateCategoryName,
  validateEmail,
  validateMemo,
  validateNickname,
  validatePassword,
  validatePasswordConfirm,
} from './validation';

describe('회원가입 입력 검증 (FR-01)', () => {
  it('FR-01 이메일 형식을 검사한다', () => {
    expect(validateEmail('user@example.com')).toBeNull();
    expect(validateEmail('  ')).toBe('이메일을 입력해 주세요.');
    expect(validateEmail('user@example')).toBe('이메일 형식이 올바르지 않습니다.');
  });

  it('FR-01 비밀번호는 8자 이상이며 영문과 숫자를 모두 포함해야 한다', () => {
    expect(validatePassword('abc12345')).toBeNull();
    expect(validatePassword('abc1234')).toBe('비밀번호는 8자 이상이어야 합니다.');
    expect(validatePassword('abcdefgh')).toBe('비밀번호에는 영문과 숫자가 모두 포함되어야 합니다.');
    expect(validatePassword('12345678')).toBe('비밀번호에는 영문과 숫자가 모두 포함되어야 합니다.');
  });

  it('FR-01 비밀번호 확인이 일치해야 한다', () => {
    expect(validatePasswordConfirm('abc12345', 'abc12345')).toBeNull();
    expect(validatePasswordConfirm('abc12345', 'abc12346')).toBe('비밀번호가 일치하지 않습니다.');
  });

  it('FR-01 닉네임은 비어 있으면 안 된다', () => {
    expect(validateNickname(' 가계 ')).toBeNull();
    expect(validateNickname('   ')).toBe('닉네임을 입력해 주세요.');
  });
});

describe('카테고리와 메모 검증 (FR-07, FR-10)', () => {
  it('FR-07 카테고리 이름은 공백을 제거한 뒤 1~20자여야 한다', () => {
    expect(validateCategoryName('  식비  ')).toBeNull();
    expect(validateCategoryName('   ')).toBe('카테고리 이름을 입력해 주세요.');
    expect(validateCategoryName('가'.repeat(20))).toBeNull();
    expect(validateCategoryName('가'.repeat(21))).toBe('카테고리 이름은 20자 이하여야 합니다.');
  });

  it('FR-10 메모는 최대 200자이다', () => {
    expect(validateMemo('a'.repeat(200))).toBeNull();
    expect(validateMemo('a'.repeat(201))).toBe('메모는 200자 이하여야 합니다.');
  });
});
