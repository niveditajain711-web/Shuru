/** The Shuru brand: a green tile with a "start" arrow, the wordmark, a turmeric dot, and "शुरू" (Hindi for "start"). */
export function Logo() {
  return (
    <>
      <svg className="logo-mark" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="currentColor" />
        <path
          d="M10.5 21.5 21.5 10.5M12.5 10.5h9v9"
          fill="none"
          stroke="#fff"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="logo-word">
        Shuru
        <span className="logo-dot" aria-hidden="true">
          .
        </span>
      </span>
      <span className="logo-hindi" lang="hi" aria-hidden="true">
        शुरू
      </span>
    </>
  );
}
