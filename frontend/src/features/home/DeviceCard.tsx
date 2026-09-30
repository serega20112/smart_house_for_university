/** Compact device card with its switch and optional mode selector. */

import { Badge } from "../../components/Badge";
import { DeviceIcon } from "../../components/DeviceIcon";
import { Toggle } from "../../components/Toggle";
import * as api from "../../services/api";
import type { Capability, Device } from "../../services/types";

const MODE_LABELS: Record<Capability, string> = {
  ON: "Вкл",
  OFF: "Выкл",
  COOL: "Охлаждение",
  HEAT: "Нагрев",
};

const TYPE_LABELS: Record<Device["type"], string> = {
  LIGHT: "Свет",
  FAN: "Вентилятор",
  HUMIDIFIER: "Увлажнитель",
  AIR_CONDITIONER: "Кондиционер",
  HEATER: "Обогреватель",
  OUTLET: "Розетка",
  OTHER: "Прочее",
};

const STATUS_LABELS: Record<Device["status"], string> = {
  ON: "Включено",
  OFF: "Выключено",
  COOL: "Охлаждение",
  HEAT: "Нагрев",
  UNAVAILABLE: "Недоступно",
};

const STATUS_TONES: Record<Device["status"], "ok" | "warn" | "idle" | "bad"> = {
  ON: "ok",
  OFF: "idle",
  COOL: "ok",
  HEAT: "warn",
  UNAVAILABLE: "bad",
};

interface DeviceCardProps {
  device: Device;
  onError: (message: string) => void;
  onChanged: () => void;
}

export function DeviceCard({ device, onError, onChanged }: DeviceCardProps) {
  const unavailable = device.status === "UNAVAILABLE";
  const active =
    device.status === "ON" || device.status === "COOL" || device.status === "HEAT";
  const modes = device.capabilities.filter((capability) => capability !== "OFF");

  async function run(action: () => Promise<unknown>): Promise<void> {
    try {
      await action();
      onChanged();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Команда не выполнена");
    }
  }

  return (
    <article className={`device ${active ? "device--active" : ""}`.trim()}>
      <span className="device__glow" data-status={device.status} />

      <header className="device__head">
        <DeviceIcon type={device.type} active={active} />
        <div className="device__headline">
          <h3 className="device__name">{device.name}</h3>
          <p className="device__meta">
            {TYPE_LABELS[device.type]} · Relay {device.physical_channel}
          </p>
        </div>
        <Badge tone={STATUS_TONES[device.status]} label={STATUS_LABELS[device.status]} />
      </header>

      {modes.length > 1 ? (
        <div className="device__modes">
          {modes.map((mode) => (
            <button
              key={mode}
              type="button"
              aria-pressed={device.status === mode}
              className={`chip ${device.status === mode ? "chip--active" : ""}`.trim()}
              disabled={unavailable}
              onClick={() => void run(() => api.setDeviceMode(device.id, mode))}
            >
              {MODE_LABELS[mode]}
            </button>
          ))}
        </div>
      ) : null}

      <div className="device__foot">
        <span className="device__state">{STATUS_LABELS[device.status]}</span>
        <Toggle
          checked={active}
          disabled={unavailable || !device.enabled}
          label={`Переключить ${device.name}`}
          onChange={(next) =>
            void run(() =>
              next ? api.turnDeviceOn(device.id) : api.turnDeviceOff(device.id),
            )
          }
        />
      </div>
    </article>
  );
}
