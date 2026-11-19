import type { ReactNode } from "react";

interface Option<T extends string> {
  value: T;
  label: ReactNode;
}

interface Props<T extends string> {
  label: string;
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}

/** A small either/or control, such as the language choice. */
export function Segmented<T extends string>({ label, options, value, onChange, disabled }: Props<T>) {
  return (
    <div role="group" aria-label={label} className="segmented">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          disabled={disabled}
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
