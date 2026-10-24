/**
 * Полоска доступности системы.
 *
 * Экран показывает плату и поток событий такими, какими их видит бэкенд: «своё»
 * состояние он держит в сервере и на экране выдумывать не начинает.
 */

import { Badge } from "../../components/Badge";
import type { ConnectionState } from "../../services/realtime";
import type { HomeState } from "../../services/types";

const LINK_LABELS: Record<ConnectionState, string> = {
  connecting: "Realtime: подключение",
  open: "Realtime: live",
  closed: "Realtime: переподключение",
};

interface SystemBarProps {
  state: HomeState;
  connection: ConnectionState;
  unit: "C" | "F";
  onToggleUnit: () => void;
}

/**
 * Показывает, доступны ли плата и поток событий и держит ли паузу автоматизация.
 *
 * @param props.state Живой снимок текущего аккаунта.
 * @param props.connection Состояние потока событий.
 * @param props.unit Единица температуры, которую показывает экран.
 * @param props.onToggleUnit Вызывается, когда единицу нужно поменять.
 */
export function SystemBar({ state, connection, unit, onToggleUnit }: SystemBarProps) {
  return (
    <div className="sysbar">
      <Badge
        tone={state.board_online ? "ok" : "bad"}
        label={`Плата: ${state.board_online ? "на связи" : "недоступна"}`}
      />
      {state.automation_suspended ? (
        <Badge tone="warn" label="Ручное управление" />
      ) : null}
      {state.active_scenarios.length > 0 ? (
        <Badge tone="warn" label={`Сценариев: ${state.active_scenarios.length}`} />
      ) : null}
      <button type="button" className="chip" onClick={onToggleUnit}>
        °{unit}
      </button>
      <span className={`link-state link-state--${connection}`}>
        <span className="link-state__dot" />
        {LINK_LABELS[connection]}
      </span>
    </div>
  );
}
