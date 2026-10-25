import "./home.css";
/**
 * Главный экран.
 *
 * Сама страница о конкретном доме не знает ничего: какие карточки показать, в каком
 * порядке и под каким личным заголовком — всё это приходит из раскладки, сохранённой за
 * вошедшим аккаунтом. Здесь только рамка, полоса состояния и два куска подвала: сводка
 * автоматики и активные сценарии.
 */

import { useCallback, useEffect, useState } from "react";

import { Dashboard, SystemBar } from "@/widgets/home";
import { DashboardEditor } from "@/features/dashboard-edit";
import { useHomeState } from "@/entities/home";
import { useSession } from "@/entities/session";
import * as api from "@/shared/api/client";
import { firstNameOf } from "@/shared/lib/display";
import { formatBand, formatIn, formatMoment } from "@/shared/lib/format";
import { describeActions, scenarioStatusLabel, scenarioStatusTone } from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import type { Board, Widget } from "@/shared/api/types";
import { Badge } from "@/shared/ui";

export function HomePage() {
  const { profile, preferences } = useSession();
  const { state, loading, error, connection, syncedAt, refresh } = useHomeState();
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [boards, setBoards] = useState<Board[]>([]);
  const [editing, setEditing] = useState(false);

  /**
   * Читает раскладку экрана и платы: без них плитка не знает, чей канал показать.
   */
  const loadSide = useCallback(async () => {
    try {
      setWidgets((await api.fetchDashboard()).widgets);
    } catch {
      setWidgets([]);
    }
    try {
      setBoards(await api.fetchBoards());
    } catch {
      setBoards([]);
    }
  }, []);

  useEffect(() => {
    void loadSide();
  }, [loadSide]);

  /**
   * Закрывает настройку и перечитывает раскладку: экран показывает то, что сервер принял.
   */
  const finishEditing = useCallback(async () => {
    setEditing(false);
    await loadSide();
  }, [loadSide]);

  const automation = state?.automation;

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <p className="page__eyebrow">Главный экран</p>
          <h1 className="page__title">
            {profile ? firstNameOf(profile.display_name) : "Дом"}
          </h1>
        </div>
        <div className="home__actions">
          <SystemBar state={state} connection={connection} syncedAt={syncedAt} />
          <button
            type="button"
            className="button button--ghost"
            onClick={() => {
              void refresh();
              notify("Состояние перечитано", "info");
            }}
          >
            Обновить
          </button>
          <button
            type="button"
            className={editing ? "button button--primary" : "button"}
            aria-pressed={editing}
            onClick={() => setEditing((current) => !current)}
          >
            {editing ? "Закрыть настройку" : "Настроить экран"}
          </button>
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      {editing ? (
        <DashboardEditor
          widgets={widgets}
          devices={state?.devices ?? []}
          onSaved={() => void finishEditing()}
          onCancel={() => setEditing(false)}
        />
      ) : null}

      <Dashboard
        widgets={widgets}
        state={state}
        preferences={preferences}
        boards={boards}
        loading={loading}
        onChanged={() => void refresh()}
      />

      {automation ? (
        <div className="rail-split">
          <section className="facts-card">
            <h2 className="facts-card__title">Автоматизация</h2>
            <dl className="facts">
              <div className="facts__row">
                <dt>Режим</dt>
                <dd>
                  <Badge
                    tone={automation.enabled ? "ok" : "idle"}
                    label={automation.enabled ? "Включена" : "Выключена"}
                  />
                </dd>
              </div>
              <div className="facts__row">
                <dt>Цель по температуре</dt>
                <dd>{automation.target_temperature.toFixed(1)}°C</dd>
              </div>
              <div className="facts__row">
                <dt>Коридор</dt>
                <dd>{formatBand(automation, preferences?.temperature_unit ?? "C")}</dd>
              </div>
              <div className="facts__row">
                <dt>Цель по влажности</dt>
                <dd>
                  {automation.target_humidity.toFixed(0)}% · ±{automation.humidity_tolerance.toFixed(0)}%
                </dd>
              </div>
              <div className="facts__row">
                <dt>Участников</dt>
                <dd>{automation.participating_device_ids.length}</dd>
              </div>
            </dl>
          </section>

          <section className="facts-card">
            <h2 className="facts-card__title">Активные сценарии</h2>
            {(state?.active_scenarios.length ?? 0) === 0 ? (
              <p className="empty">Ни одного отложенного действия.</p>
            ) : (
              <ul className="list">
                {state?.active_scenarios.map((scenario) => (
                  <li key={scenario.id} className="list__item">
                    <div>
                      <span className="list__title">
                        {scenario.target ?? describeActions(scenario.actions)}
                      </span>
                      <span className="list__note">
                        старт {formatMoment(scenario.start_at)} · {formatIn(scenario.start_at)}
                      </span>
                    </div>
                    <Badge
                      tone={scenarioStatusTone(scenario.status)}
                      label={scenarioStatusLabel(scenario.status)}
                    />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
