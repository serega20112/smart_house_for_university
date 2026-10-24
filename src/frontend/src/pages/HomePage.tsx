/**
 * Главный экран.
 *
 * Сама страница о конкретном доме не знает ничего: какие карточки показать, в
 * каком порядке и под каким именем — всё это приходит из раскладки, сохранённой за
 * вошедшим аккаунтом.
 */

import { useCallback, useEffect, useState } from "react";

import { Badge } from "../components/Badge";
import { Card } from "../components/Card";
import { formatMoment } from "../features/climate/format";
import { useSession } from "../features/auth/SessionProvider";
import { Dashboard } from "../features/home/Dashboard";
import { SystemBar } from "../features/home/SystemBar";
import { useHomeState } from "../features/home/useHomeState";
import * as api from "../services/api";
import type { Automation, Widget } from "../services/types";

const DEFAULT_TITLE = "Главная";

/**
 * Возвращает текстом диапазон, в котором автоматизации позволено держать цель.
 *
 * @param automation Настройка, из которой берутся цель и допуск.
 * @returns Фраза вида «21.0–23.0°C».
 */
function formatBand(automation: Automation): string {
  const from = automation.target_temperature - automation.temperature_tolerance;
  const to = automation.target_temperature + automation.temperature_tolerance;
  return `${from.toFixed(1)}–${to.toFixed(1)}°C`;
}

export function HomePage() {
  const { profile, preferences, refreshPreferences } = useSession();
  const { state, loading, error, connection, refresh } = useHomeState();
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [unit, setUnit] = useState<"C" | "F">(preferences?.temperature_unit ?? "C");

  const loadWidgets = useCallback(async () => {
    try {
      setWidgets((await api.fetchDashboard()).widgets);
    } catch {
      setWidgets([]);
    }
  }, []);

  useEffect(() => {
    void loadWidgets();
  }, [loadWidgets]);

  const toggleUnit = useCallback(async () => {
    const next = unit === "C" ? "F" : "C";
    setUnit(next);
    await api.updatePreferences({ temperature_unit: next });
    await refreshPreferences();
  }, [refreshPreferences, unit]);

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">
            {profile ? `Привет, ${profile.display_name}` : DEFAULT_TITLE}
          </h1>
          <p className="page__subtitle">Состояние дома в реальном времени</p>
        </div>
        <SystemBar state={state} connection={connection} unit={unit} onToggleUnit={toggleUnit} />
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}

      <Dashboard
        widgets={widgets}
        state={state}
        preferences={preferences ? { ...preferences, temperature_unit: unit } : null}
        loading={loading}
        onError={setNotice}
        onChanged={() => void refresh()}
      />

      <div className="split">
        <Card title="Автоматизация" hint="Гистерезис и приоритеты">
          <dl className="facts">
            <div className="facts__row">
              <dt>AUTO</dt>
              <dd>
                <Badge
                  tone={state.automation.enabled ? "ok" : "idle"}
                  label={state.automation.enabled ? "ON" : "OFF"}
                />
              </dd>
            </div>
            <div className="facts__row">
              <dt>Цель</dt>
              <dd>{state.automation.target_temperature.toFixed(1)}°C</dd>
            </div>
            <div className="facts__row">
              <dt>Диапазон</dt>
              <dd>{formatBand(state.automation)}</dd>
            </div>
            <div className="facts__row">
              <dt>Влажность</dt>
              <dd>
                {state.automation.target_humidity.toFixed(0)}% · ±
                {state.automation.humidity_tolerance.toFixed(0)}%
              </dd>
            </div>
            <div className="facts__row">
              <dt>Ручное управление</dt>
              <dd>{state.automation_suspended ? "приоритет" : "нет"}</dd>
            </div>
          </dl>
        </Card>

        <Card title="Сценарии" hint="Временные задачи">
          {state.active_scenarios.length === 0 ? (
            <p className="empty">Активных сценариев нет</p>
          ) : (
            <ul className="list">
              {state.active_scenarios.map((scenario) => (
                <li key={scenario.id} className="list__item">
                  <div>
                    <span className="list__title">
                      #{scenario.id} · {scenario.status}
                    </span>
                    <span className="list__note">
                      старт {formatMoment(scenario.start_at)} ·{" "}
                      {scenario.actions.map((action) => action.capability).join(", ") ||
                        "без действий"}
                    </span>
                  </div>
                  <Badge tone="warn" label="RUNNING" />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
