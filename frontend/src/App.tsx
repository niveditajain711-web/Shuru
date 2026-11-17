import { useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import type { Run } from "./api/types";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { DomainStep } from "./components/DomainStep";
import { ErrorMessage } from "./components/ErrorMessage";
import { IdeaStep } from "./components/IdeaStep";
import { Loading } from "./components/Loading";
import { PreviewStep } from "./components/PreviewStep";
import { ReviewStep } from "./components/ReviewStep";
import { Stepper } from "./components/Stepper";
import { useAction } from "./hooks/useAction";
import { isStepAvailable, naturalStep, STEPS, type Step } from "./navigation";
import { navigate, useRoute } from "./routing";

export function App() {
  const route = useRoute();
  const [run, setRun] = useState<Run | null>(null);
  const [confirmingStartOver, setConfirmingStartOver] = useState(false);
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
        return activeRun && <PreviewStep run={activeRun} onUpdated={updateRun} onStartOver={requestStartOver} />;
    }
  }

  return (
    <div className="page">
      <header className="site-header">
        <button type="button" className="logo" title="Start a new site" onClick={requestStartOver}>
          Shuru
        </button>
        <Stepper current={step} run={activeRun} onNavigate={(target) => activeRun && navigate(activeRun.id, target)} />
      </header>
      <main ref={main}>{renderStep()}</main>

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
    </div>
  );
}
