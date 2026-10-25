import "./automation.css";
/**
 * Экран автоматизации.
 *
 * Автоматика держит две цели: температуру и влажность. Всё остальное — участники и
 * допуски. Экран берёт живые значения из того же снимка, что и главный экран, чтобы
 * линейка цели показывала реальность, а не только намерение.
 */

import { useCallback, useState } from "react";

import { AutomationForm } from "@/features/automation-edit";
import { useHomeState } from "@/entities/home";
import { useSession } from "@/entities/session";
import { formatBand } from "@/shared/lib/format";
import { Badge } from "@/shared/ui";

export function AutomationPage() {
  const { preferences } = useSession();
  const { state, loading, error, refresh } = useHomeState();
  const [savedAt, setSavedAt] = useState<number | null>(null);

  /**
   * Перечитывает дом после того, как настройка ушла на сервер.
   */
  const finish = useCallback(async () => {
    await refresh();
    setSavedAt(Date.now());
  }, [refresh]);

  const unit = preferences?.temperature_unit ?? "C";

  if (loading && state === null) {
    return (
      <div className="page">
        <header className="page__head">
          <div>
            <p className="page__eyebrow">Климат</p>
            <h1 className="page__title">Автоматизация</h1>
          </div>
        </header>
        <p className="notice">Читаю настройку…</p>
      </div>
    );
  }

  if (state === null) {
    return (
      <div className="page">
        <header className="page__head">
          <div>
            <p className="page__eyebrow">Климат</p>
            <h1 className="page__title">Автоматизация</h1>
          </div>
        </header>
        <p className="notice notice--bad">{error ?? "Настройка не прочиталась"}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <p className="page__eyebrow">Климат</p>
          <h1 className="page__title">Автоматизация</h1>
          <p className="page__subtitle">
            {state.automation.enabled
              ? `Держит ${formatBand(state.automation, unit)}`
              : "Выключена: цели не держатся сами"}
          </p>
        </div>
        <div className="automation__head">
          <Badge
            tone={state.automation.enabled ? "ok" : "idle"}
            label={state.automation.enabled ? "Работает" : "Выключена"}
          />
          {state.automation_suspended ? <Badge tone="warn" label="Ручная пауза" /> : null}
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <AutomationForm
        automation={state.automation}
        reading={state.reading}
        devices={state.devices}
        unit={unit}
        onSaved={() => void finish()}
      />

      {savedAt !== null ? (
        <p className="automation__saved">Настройка принята сервером.</p>
      ) : null}
    </div>
  );
}
