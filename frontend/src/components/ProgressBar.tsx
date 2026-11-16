export const STEPS = ["Idea", "Domain", "Preview"] as const;
export type Step = "idea" | "domain" | "preview";

const STEP_ORDER: Step[] = ["idea", "domain", "preview"];

export function ProgressBar({ current }: { current: Step }) {
  const currentIndex = STEP_ORDER.indexOf(current);
  return (
    <ol className="progress" aria-label="Progress">
      {STEPS.map((label, index) => (
        <li
          key={label}
          className={index <= currentIndex ? "done" : undefined}
          aria-current={index === currentIndex ? "step" : undefined}
        >
          {label}
        </li>
      ))}
    </ol>
  );
}
