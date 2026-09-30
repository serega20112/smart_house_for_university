/** Automation page. */

import { useState } from "react";

import { useHomeState } from "../features/home/useHomeState";
import { AutomationForm } from "../features/automation/AutomationForm";

export function AutomationPage() {
  const { state, refresh } = useHomeState();
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Автоматизация</h1>
          <p className="page__subtitle">Цели, допуски и участие устройств</p>
        </div>
      </header>

      {notice ? <p className="notice">{notice}</p> : null}
      {error ? <p className="notice notice--bad">{error}</p> : null}

      <AutomationForm
        automation={state.automation}
        devices={state.devices}
        onSaved={(message) => {
          setNotice(message);
          setError(null);
          void refresh();
        }}
        onError={setError}
      />
    </div>
  );
}
