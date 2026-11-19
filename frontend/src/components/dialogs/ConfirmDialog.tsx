import { useEffect, useRef, type ReactNode } from "react";

interface Props {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** A modal confirmation built on the native `<dialog>`, which traps focus and closes on Escape. */
export function ConfirmDialog({ open, title, children, confirmLabel, cancelLabel, onConfirm, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby="confirm-title"
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
    >
      <h2 id="confirm-title">{title}</h2>
      {children}
      <div className="actions">
        <button type="button" onClick={onConfirm}>
          {confirmLabel}
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          {cancelLabel}
        </button>
      </div>
    </dialog>
  );
}
