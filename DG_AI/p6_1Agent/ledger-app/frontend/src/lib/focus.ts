/**
 * 폼 제출 후 첫 번째 오류 필드로 포커스를 옮깁니다 (NFR-18).
 * React가 오류 상태를 그린 뒤에 실행되도록 다음 작업으로 미룹니다.
 */
export function focusFirstInvalid(form: HTMLFormElement | null): void {
  if (!form) return;
  setTimeout(() => {
    const target = form.querySelector<HTMLElement>('[aria-invalid="true"]');
    target?.focus();
  }, 0);
}
