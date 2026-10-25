import "./system-bar.css";
/**
 * Полоска состояния дома.
 *
 * Экран показывает плату, поток событий и паузу автоматизации такими, какими их видит
 * бэкенд: «своё» состояние интерфейс держит на сервере и выдумывать его не начинает.
 * Отдельно здесь единицы температуры — то, чем человек пользуется каждый день.
 */

import { usePreferences } from "@/features/preferences";
import { boardStatusLabel } from "@/shared/lib/labels";
import { formatAgo } from "@/shared/lib/format";
import { CONNECTION_LABELS, type ConnectionState } from "@/shared/realtime/use-realtime";
import type { HomeState, TemperatureUnit } from "@/shared/api/types";
import { Badge } from "@/shared/ui";

const UNITS: readonly TemperatureUnit[] = ["C", "F"];

interface SystemBarProps {
  state: HomeState | null;
  connection: ConnectionState;
  syncedAt: number | null;
}

/**
 * Возвращает полоску доступности дома и переключатель единиц.
 *
 * @param props.state Живой снимок или None, пока он не прочитан.
 * @param props.connection Состояние потока событий.
 * @param props.syncedAt Момент последнего удачного чтения дома.
 */
export function SystemBar({ state, connection, syncedAt }: SystemBarProps) {
  const { unit, busy, changeUnit } = usePreferences();

  return (
    <div className="sysbar">
      {state ? (
        <>
          <Badge
            tone={state.board_online ? "ok" : "bad"}
            label={`Плата: ${boardStatusLabel(state.board_online)}`}
          />
          {state.automation_suspended ? <Badge tone="warn" label="Ручное управление" /> : null}
          {state.active_scenarios.length > 0 ? (
            <Badge tone="warn" label={`Сценариев: ${state.active_scenarios.length}`} />
          ) : null}
        </>
      ) : (
        <Badge tone="idle" label="Читаю состояние…" />
      )}

      <div className="segmented" role="group" aria-label="Единицы температуры">
        {UNITS.map((option) => (
          <button
            key={option}
            type="button"
            disabled={busy}
            aria-pressed={option === unit}
            className={`segmented__option ${option === unit ? "segmented__option--on" : ""}`.trim()}
            onClick={() => option !== unit && void changeUnit(option)}
          >
            °{option}
          </button>
        ))}
      </div>

      <span className={`sysbar__link sysbar__link--${connection}`}>
        <span className="sysbar__dot" aria-hidden="true" />
        {`События: ${CONNECTION_LABELS[connection]}`}
        {syncedAt !== null ? <span className="sysbar__sync">обновлено {formatAgo(new Date(syncedAt).toISOString())}</span> : null}
      </span>
    </div>
  );
}
