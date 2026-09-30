/** Main screen: availability, climate, devices and the command chat. */

import { useState } from "react";

import { Badge } from "../components/Badge";
import { Card } from "../components/Card";
import { Skeleton } from "../components/Skeleton";
import { formatMoment } from "../features/climate/format";
import { Climate } from "../features/home/ClimateCards";
import { CommandChat } from "../features/home/CommandChat";
import { DeviceGrid } from "../features/home/DeviceGrid";
import { SystemBar } from "../features/home/SystemBar";
import { useHomeState } from "../features/home/useHomeState";

export function HomePage() {
  const { state, loading, error, connection, refresh } = useHomeState();
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Главная</h1>
          <p className="page__subtitle">Состояние дома в реальном времени</p>
        </div>
        <SystemBar state={state} connection={connection} />
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}

      <Climate state={state} />

      {loading ? <Skeleton /> : null}

      {!loading ? (
        <DeviceGrid
          devices={state.devices}
          onError={setNotice}
          onChanged={() => void refresh()}
        />
      ) : null}

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
              <dd>
                {state.automation.min_temperature.toFixed(1)}–
                {state.automation.max_temperature.toFixed(1)}°C
              </dd>
            </div>
            <div className="facts__row">
              <dt>Влажность</dt>
              <dd>
                {state.automation.target_humidity.toFixed(0)}% ·{" "}
                {state.automation.min_humidity.toFixed(0)}–
                {state.automation.max_humidity.toFixed(0)}%
              </dd>
            </div>
            <div className="facts__row">
              <dt>Ручное управление</dt>
              <dd>{state.manual_override ? "приоритет" : "нет"}</dd>
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

      <CommandChat />
    </div>
  );
}
