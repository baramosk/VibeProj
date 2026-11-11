import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  block?: boolean;
}

/** 공용 버튼. 최소 높이 44px, hover, focus-visible, disabled 상태를 모두 정의합니다. */
export function Button({ variant = 'primary', block = false, className, type = 'button', ...rest }: ButtonProps) {
  const classes = ['btn', `btn--${variant}`, block ? 'btn--block' : '', className ?? ''].filter(Boolean).join(' ');
  return <button type={type} className={classes} {...rest} />;
}
