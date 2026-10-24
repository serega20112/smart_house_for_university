/**
 * Страница сценариев: список и отмена временных задач.
 *
 * Сценарий человек ставит словами в чате команды, а здесь он только видит, что
 * обещание ещё стоит, и снимает его раньше срока.
 */

import { useCallback, useEffect, useState } from "react";

import { Card } from "../components/Card";
import { formatMoment } from "../features/climate/format";
import * as api from "../services/api";
import { useRealtime } from "../services/realtime";
import { needsReload } from "../features/home/reducer";
import type { Scenario } from "../services/types";

export function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setScenarios(await api.fetchScenarios());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось загрузить сценарии");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useRealtime({
    enabled: true,
    onMessage: (message) => {
      if (needsReload(message.type)) {
        void load();
      }
    },
  });

  /**
   * Отменяет сценарий.
   *
   * @param scenarioId Идентификатор сценария.
   * @returns Ничего: список перечитывается после ответа сервера.
   */
  async function cancel(scenarioId: string): Promise<void> {
    try {
      await api.cancelScenario(scenarioId);
      await load();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось отменить сценарий");
    }
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Сценарии</h1>
          <p className="page__subtitle">Временные задачи с приоритетом над автоматизацией</p>
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <Card title="Активные сценарии">
        {scenarios.length === 0 ? (
          <p className="empty">Активных сценариев нет</p>
        ) : (
          <ul className="list">
            {scenarios.map((scenario) => (
              <li key={scenario.id} className="list__item">
                <div>
                  <span className="list__title">
                    #{scenario.id} · {scenario.status}
                  </span>
                  <span className="list__note">
                    старт {formatMoment(scenario.start_at)} ·{" "}
                    {scenario.actions.map((action) => action.capability).join(", ") || "без действий"}
                  </span>
                </div>
                <button
                  className="button button--ghost"
                  type="button"
                  onClick={() => void cancel(scenario.id)}
                >
                  Отменить
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
