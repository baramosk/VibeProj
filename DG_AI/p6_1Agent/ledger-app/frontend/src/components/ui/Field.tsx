import { useId, type ReactNode } from 'react';

export interface FieldControlProps {
  id: string;
  'aria-invalid': boolean;
  'aria-describedby': string | undefined;
  'aria-required': boolean | undefined;
}

interface FieldProps {
  label: string;
  hint?: string;
  error?: string | null;
  required?: boolean;
  /** 라벨과 메시지를 연결한 입력 컨트롤을 만듭니다. */
  children: (control: FieldControlProps) => ReactNode;
  className?: string;
}

/**
 * 폼 필드 공용 래퍼 (NFR-18). label을 컨트롤에 연결하고,
 * 안내 문구와 오류 메시지를 aria-describedby로 묶어 스크린 리더가 함께 읽게 합니다.
 */
export function Field({ label, hint, error, required = false, children, className }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={['field', error ? 'field--invalid' : '', className ?? ''].filter(Boolean).join(' ')}>
      <label htmlFor={id} className="field__label">
        {label}
        {required && (
          <>
            <span className="field__required" aria-hidden="true">
              {' *'}
            </span>
            <span className="sr-only"> (필수)</span>
          </>
        )}
      </label>
      {children({
        id,
        'aria-invalid': Boolean(error),
        'aria-describedby': describedBy,
        'aria-required': required || undefined,
      })}
      {hint && (
        <p id={hintId} className="field__hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="field__error">
          <span aria-hidden="true">! </span>
          {error}
        </p>
      )}
    </div>
  );
}

interface RadioOption<T extends string> {
  value: T;
  label: string;
}

interface RadioGroupProps<T extends string> {
  name: string;
  legend: string;
  value: T;
  options: RadioOption<T>[];
  onChange: (value: T) => void;
  disabled?: boolean;
  /** 색상 스와치처럼 보조 표시가 필요한 옵션의 렌더러 */
  renderOption?: (option: RadioOption<T>) => ReactNode;
  className?: string;
}

/** 라디오 묶음. fieldset과 legend로 그룹 이름을 제공합니다. */
export function RadioGroup<T extends string>({
  name,
  legend,
  value,
  options,
  onChange,
  disabled = false,
  renderOption,
  className,
}: RadioGroupProps<T>) {
  return (
    <fieldset className={['radio-group', className ?? ''].filter(Boolean).join(' ')} disabled={disabled}>
      <legend className="field__label">{legend}</legend>
      <div className="radio-group__options">
        {options.map((option) => {
          const inputId = `${name}-${option.value}`;
          return (
            <label key={option.value} htmlFor={inputId} className="radio-option">
              <input
                id={inputId}
                type="radio"
                name={name}
                value={option.value}
                checked={value === option.value}
                onChange={() => onChange(option.value)}
              />
              <span className="radio-option__text">{renderOption ? renderOption(option) : option.label}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
