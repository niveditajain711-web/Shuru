import type { Run } from "../../api/types";
import { isStepAvailable, STEPS, stepIndex, stepStatus, unavailableHint, type Step } from "../../lib/navigation";

interface Props {
  current: Step;
  run: Run | null;
  onNavigate: (step: Step) => void;
}

/** Shows where the user is. Finished steps that are still open can be clicked to go back. */
export function Stepper({ current, run, onNavigate }: Props) {
  return (
    <nav aria-label="Progress" className="stepper">
      <p className="step-count">
        Step {stepIndex(current) + 1} of {STEPS.length}
      </p>
      <ol>
        {STEPS.map(({ id, label }, index) => {
          const status = stepStatus(id, current, run);
          const clickable = status !== "current" && isStepAvailable(id, run);
          const marker = status === "done" ? "✓" : index + 1;
          const hint = !clickable && status !== "current" ? unavailableHint(id, run) : "";

          const content = (
            <>
              <span className="step-marker" aria-hidden="true">
                {marker}
              </span>
              <span className="step-label">{label}</span>
              {status === "done" && <span className="sr-only"> (completed)</span>}
              {hint && <span className="sr-only"> ({hint})</span>}
            </>
          );

          return (
            <li key={id} className={`step ${status}`} aria-current={status === "current" ? "step" : undefined}>
              {clickable ? (
                <button type="button" className="step-button" onClick={() => onNavigate(id)}>
                  {content}
                </button>
              ) : (
                <span className="step-button" title={hint || undefined}>
                  {content}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
