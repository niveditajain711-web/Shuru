import { useEffect, useRef } from "react";
import { ContactForm } from "../forms/ContactForm";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Support modal built on the native `<dialog>`: showModal() traps Tab, makes the page behind inert,
 * closes on Escape, and returns focus to the element that opened it (the Support link).
 */
export function SupportDialog({ open, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="support-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="support-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      // A click on the dialog element itself (not its content) is a click on the backdrop.
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="support-body">
        <div className="support-head">
          <h2 id="support-title">Support</h2>
          <button type="button" className="icon-button" aria-label="Close" onClick={onClose}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <p className="lead">Hi, need help? We reply within 1-2 days.</p>
        <ContactForm open={open} onClose={onClose} />
      </div>
    </dialog>
  );
}
