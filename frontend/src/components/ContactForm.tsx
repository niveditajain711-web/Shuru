import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";
import { Loading } from "./Loading";

const MAX_MESSAGE_LENGTH = 5000;

interface Props {
  /** Whether the surrounding modal is open; reopening after a send starts a fresh form. */
  open: boolean;
  onClose: () => void;
}

/** Contact form: the backend emails the message to the Shuru mailbox. No mail credentials are in the browser. */
export function ContactForm({ open, onClose }: Props) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState(""); // honeypot, hidden from people
  const [sent, setSent] = useState(false);
  const { run: sendContact, loading, error } = useAction(api.sendContact);

  useEffect(() => {
    if (open) setSent(false);
  }, [open]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const result = await sendContact({ name: name.trim(), email: email.trim(), message: message.trim(), website });
    if (result) {
      setSent(true);
      setName("");
      setEmail("");
      setMessage("");
    }
  }

  if (sent) {
    return (
      <div className="contact-sent">
        <p className="notice" role="status">
          Thanks! Your message has been sent. We'll reply by email.
        </p>
        <div className="actions">
          <button type="button" onClick={onClose}>
            Close
          </button>
          <button type="button" className="link" onClick={() => setSent(false)}>
            Send another message
          </button>
        </div>
      </div>
    );
  }

  return (
    <form className="contact-form" onSubmit={handleSubmit} aria-labelledby="support-title">

      <div className="field">
        <label htmlFor="contact-name">Your name</label>
        <input
          id="contact-name"
          type="text"
          autoComplete="name"
          maxLength={100}
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          disabled={loading}
        />
      </div>

      <div className="field">
        <label htmlFor="contact-email">Your email</label>
        <input
          id="contact-email"
          type="email"
          autoComplete="email"
          maxLength={254}
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={loading}
        />
      </div>

      <div className="field">
        <label htmlFor="contact-message">Message</label>
        <textarea
          id="contact-message"
          rows={4}
          maxLength={MAX_MESSAGE_LENGTH}
          required
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          disabled={loading}
        />
      </div>

      {/* Honeypot: people never see or fill this; bots often do, and the server then drops the message. */}
      <div className="hp" aria-hidden="true">
        <label htmlFor="contact-website">Website</label>
        <input
          id="contact-website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(event) => setWebsite(event.target.value)}
        />
      </div>

      <ErrorMessage message={error} />
      {loading ? (
        <Loading message="Sending your message…" />
      ) : (
        <div className="actions">
          <button type="submit" disabled={name.trim() === "" || email.trim() === "" || message.trim() === ""}>
            Send message
          </button>
        </div>
      )}
    </form>
  );
}
