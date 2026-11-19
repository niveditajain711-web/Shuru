import { useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import type { Run } from "./api/types";
import { ConfirmDialog } from "./components/dialogs/ConfirmDialog";
import { CheckoutStep } from "./components/steps/CheckoutStep";
import { DomainStep } from "./components/steps/DomainStep";
import { ErrorMessage } from "./components/ui/ErrorMessage";
import { IdeaStep } from "./components/steps/IdeaStep";
import { Loading } from "./components/ui/Loading";
import { Logo } from "./components/ui/Logo";
import { PreviewStep } from "./components/steps/PreviewStep";
import { ReviewStep } from "./components/steps/ReviewStep";
import { SupportDialog } from "./components/dialogs/SupportDialog";
import { Stepper } from "./components/ui/Stepper";
import { useAction } from "./hooks/useAction";
import { isStepAvailable, naturalStep, STEPS, type Step } from "./lib/navigation";
import { navigate, useRoute } from "./lib/routing";

export function App() {
  const route = useRoute();
  const [run, setRun] = useState<Run | null>(null);
  const [confirmingStartOver, setConfirmingStartOver] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);
  const { run: fetchRun, error: loadError } = useAction(api.getRun);
  const main = useRef<HTMLElement>(null);

  // The run in view is the one named by the URL. Without a run id in the URL, the user is at home.
  const activeRun = run && run.id === route.runId ? run : null;
  const step: Step =
    !activeRun || !route.step || !isStepAvailable(route.step, activeRun) ? (activeRun ? naturalStep(activeRun) : "idea") : route.step;

  // Opening a link, refreshing, or pressing Back loads the run named in the URL.
  useEffect(() => {
    const id = route.runId;
    if (!id || run?.id === id) return;
    let cancelled = false;
    void fetchRun(id).then((loaded) => {
      if (!cancelled && loaded) setRun(loaded);
    });
    return () => {
      cancelled = true;
    };
  }, [route.runId]);

  // A step that is locked or not reached yet in the URL is replaced by the step the run is at.
  useEffect(() => {
    if (activeRun && route.step !== step) navigate(activeRun.id, step, true);
  }, [activeRun, route.step, step]);

  // Each new screen gets focus and a page title, so keyboard and screen reader users know it changed.
  const heading = !route.runId || activeRun ? step : null;
  useEffect(() => {
    const h1 = main.current?.querySelector("h1");
    if (h1) {
      h1.tabIndex = -1;
      h1.focus({ preventScroll: true });
    }
    const label = STEPS.find((s) => s.id === step)?.label;
    document.title = heading && label ? `${label} · Shuru` : "Shuru";
  }, [heading, activeRun?.id]);

  function goHome() {
    setConfirmingStartOver(false);
    navigate(null, "idea");
  }

  // Starting over only changes what is on screen: the current run stays saved and reachable by its link.
  function requestStartOver() {
    if (activeRun) setConfirmingStartOver(true);
    else goHome();
  }

  function updateRun(updated: Run, nextStep?: Step) {
    setRun(updated);
    if (nextStep) navigate(updated.id, nextStep);
  }

  function renderStep() {
    if (route.runId && !activeRun) {
      return loadError ? (
        <section className="card">
          <h1>We couldn't open that site</h1>
          <ErrorMessage message={loadError} />
          <div className="actions">
            <button type="button" onClick={goHome}>
              Start a new site
            </button>
          </div>
        </section>
      ) : (
        <section className="card">
          <h1>Opening your site…</h1>
          <Loading message="Loading your progress…" />
        </section>
      );
    }

    switch (step) {
      case "idea":
        return (
          <IdeaStep
            run={activeRun}
            onCreated={(created) => updateRun(created, "idea")}
            onContinue={() => activeRun && navigate(activeRun.id, naturalStep(activeRun))}
          />
        );
      case "domain":
        return (
          activeRun && (
            <DomainStep run={activeRun} onUpdated={updateRun} onChosen={(chosen) => updateRun(chosen, "review")} />
          )
        );
      case "review":
        return (
          activeRun && (
            <ReviewStep
              run={activeRun}
              onConfirmed={(generated) => updateRun(generated, "preview")}
              onBack={() => navigate(activeRun.id, "domain")}
            />
          )
        );
      case "preview":
        return (
          activeRun && (
            <PreviewStep
              run={activeRun}
              onUpdated={updateRun}
              onBuy={() => navigate(activeRun.id, "checkout")}
              onStartOver={requestStartOver}
            />
          )
        );
      case "checkout":
        return (
          activeRun && (
            <CheckoutStep
              run={activeRun}
              onUpdated={updateRun}
              onBack={() => navigate(activeRun.id, "preview")}
              onStartOver={requestStartOver}
            />
          )
        );
    }
  }

  return (
    <>
      <header className="app-bar">
        <div className="app-bar-inner">
          <button type="button" className="logo" title="Start a new site" onClick={requestStartOver}>
            <Logo />
          </button>
          <button type="button" className="nav-link" onClick={() => setSupportOpen(true)}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M4 14v-2a8 8 0 0 1 16 0v2" />
              <rect x="3" y="14" width="4" height="6" rx="1.5" />
              <rect x="17" y="14" width="4" height="6" rx="1.5" />
              <path d="M19 20c0 1.5-2 2-5 2" />
            </svg>
            <span className="nav-link-label">Support</span>
          </button>
        </div>
      </header>
      <div className={step === "preview" && activeRun ? "page page-wide" : "page"}>
        <Stepper current={step} run={activeRun} onNavigate={(target) => activeRun && navigate(activeRun.id, target)} />
        <main ref={main}>{renderStep()}</main>
      </div>
      <SupportDialog open={supportOpen} onClose={() => setSupportOpen(false)} />

      <ConfirmDialog
        open={confirmingStartOver}
        title="Start a new site?"
        confirmLabel="Start new site"
        cancelLabel="Keep working"
        onConfirm={goHome}
        onCancel={() => setConfirmingStartOver(false)}
      >
        <p>Your current site stays saved. You can return to it with the browser Back button or its link.</p>
      </ConfirmDialog>
    </>
  );
}
