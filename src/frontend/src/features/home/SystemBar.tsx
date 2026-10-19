/** System availability strip. */

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
  unit: string;
  onToggleUnit: () => void;
}

/**
 * Shows whether the backend, the board and the event stream are reachable.
 *
 * @param props.state Live snapshot of the current account.
 * @param props.connection State of the event stream.
 * @param props.unit Temperature unit currently in use.
 * @param props.onToggleUnit Called when the unit has to be switched.
 */
export function SystemBar({ state, connection, unit, onToggleUnit }: SystemBarProps) {
  return (
    <div className="sysbar">
      <Badge tone="ok" label="Backend: Online" />
      <Badge
        tone={state.esp_online ? "ok" : "bad"}
        label={`ESP8266: ${state.esp_online ? "Online" : "Offline"}`}
      />
      {state.manual_override ? <Badge tone="warn" label="Ручное управление" /> : null}
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
