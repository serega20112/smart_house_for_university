import "./scenarios.css";
/**
 * Экран сценариев.
 *
 * Сценарий — одно обещание дому, данное на потом. Список показывает и те, что ещё ждут,
 * и те, что уже кончились: по ним видно, что дом делал и почему перестал. Отменить можно
 * только живое — завершённый сценарий остаётся записью.
 */

import { useCallback, useEffect, useState } from "react";

import { ScenarioComposer } from "@/features/scenario-schedule";
import * as api from "@/shared/api/client";
import { useRealtime } from "@/shared/realtime/use-realtime";
import { formatIn, formatMinutes, formatMoment } from "@/shared/lib/format";
import {
  COMPLETION_LABELS,
  describeActions,
  scenarioStatusLabel,
  scenarioStatusTone,
} from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import type { Scenario, ScenarioStatus } from "@/shared/api/types";
import { Badge } from "@/shared/ui";

/** Статусы, у которых есть смысл отмены. */
const CANCELLABLE: readonly ScenarioStatus[] = ["PENDING", "RUNNING"];

/** Как часто пересчитывать обратный отсчёт, даже если событий не было. */
const TICK_MS = 30_000;

export function ScenariosPage() {
  const [items, setItems] = useState<Scenario[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ScenarioStatus | "ALL">("ALL");
  const [busy, setBusy] = useState(false);
  const [, setTick] = useState(0);

  /**
   * Перечитывает все сценарии аккаунта.
   */
  const load = useCallback(async () => {
    try {
      setItems(await api.fetchScenarios());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Сценарии не прочитались");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useRealtime(() => void load());

  // Отсчёт живёт на экране, поэтому тикает сам, даже когда сервер молчит.
  useEffect(() => {
    const timer = window.setInterval(() => setTick((current) => current + 1), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  /**
   * Отменяет сценарий.
   *
   * @param scenario Сценарий, который больше не нужен.
   */
  async function cancel(scenario: Scenario): Promise<void> {
    setBusy(true);
    try {
      await api.cancelScenario(scenario.id);
      notify("Сценарий отменён", "ok");
      await load();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Отмена не прошла", "bad");
    } finally {
      setBusy(false);
    }
  }

  const statuses = Array.from(new Set(items.map((item) => item.status)));
  const visible = filter === "ALL" ? items : items.filter((item) => item.status === filter);
  const pending = items.filter((item) => CANCELLABLE.includes(item.status)).length;

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <p className="page__eyebrow">Расписание</p>
          <h1 className="page__title">Сценарии</h1>
          <p className="page__subtitle">
            {items.length === 0
              ? "Обещаний дому пока нет"
              : `${pending} живых из ${items.length} записей`}
          </p>
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <ScenarioComposer onScheduled={() => void load()} />

      <div className="scenarios__filters">
        <button
          type="button"
          className={`chip ${filter === "ALL" ? "chip--active" : ""}`.trim()}
          onClick={() => setFilter("ALL")}
        >
          Все {items.length}
        </button>
        {statuses.map((status) => (
          <button
            key={status}
            type="button"
            className={`chip ${filter === status ? "chip--active" : ""}`.trim()}
            onClick={() => setFilter(status)}
          >
            {scenarioStatusLabel(status)}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <p className="empty__title">Здесь пусто</p>
          <p>Поставьте действие в форме выше или снимите фильтр.</p>
        </div>
      ) : (
        <ul className="list">
          {visible.map((scenario) => (
            <li key={scenario.id} className="scenario">
              <div className="scenario__main">
                <p className="scenario__title">
                  {scenario.target ? `${scenario.target}: ` : ""}
                  {describeActions(scenario.actions)}
                </p>
                <p className="scenario__note">
                  начало {formatMoment(scenario.start_at)}
                  {scenario.status === "PENDING" ? ` · ${formatIn(scenario.start_at)}` : ""}
                  {scenario.duration_minutes !== null
                    ? ` · отпущено ${formatMinutes(scenario.duration_minutes)}`
                    : ""}
                  {` · после: ${COMPLETION_LABELS[scenario.completion_behavior]}`}
                </p>
              </div>

              <div className="scenario__side">
                <Badge
                  tone={scenarioStatusTone(scenario.status)}
                  label={scenarioStatusLabel(scenario.status)}
                />
                {CANCELLABLE.includes(scenario.status) ? (
                  <button
                    type="button"
                    className="button button--danger button--sm"
                    disabled={busy}
                    onClick={() => void cancel(scenario)}
                  >
                    Отменить
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
