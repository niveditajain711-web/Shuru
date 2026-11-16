import { useState } from "react";
import type { Run } from "./api/types";
import { DomainStep } from "./components/DomainStep";
import { IdeaStep } from "./components/IdeaStep";
import { PreviewStep } from "./components/PreviewStep";
import { ProgressBar, type Step } from "./components/ProgressBar";

export function App() {
  const [step, setStep] = useState<Step>("idea");
  const [run, setRun] = useState<Run | null>(null);

  function handleChosen(updated: Run) {
    setRun(updated);
    setStep("preview");
  }

  return (
    <div className="page">
      <header>
        <span className="logo">Shuru</span>
        <ProgressBar current={step} />
      </header>
      <main>
        {step === "idea" && <IdeaStep run={run} onCreated={setRun} onContinue={() => setStep("domain")} />}
        {step === "domain" && run && <DomainStep run={run} onChosen={handleChosen} />}
        {step === "preview" && run && <PreviewStep run={run} onUpdated={setRun} />}
      </main>
    </div>
  );
}
