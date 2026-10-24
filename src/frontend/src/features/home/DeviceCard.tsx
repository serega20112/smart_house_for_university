/**
 * Компактная карточка устройства с переключателем и выбором режима.
 *
 * Карточка умеет ровно то, что разрешило приложение: список способностей приходит
 * с сервера, и никаких догадок о том, что устройство «наверное умеет выключаться»,
 * здесь не строится.
 */

import { Badge } from "../../components/Badge";
import { DeviceIcon } from "../../components/DeviceIcon";
import { Toggle } from "../../components/Toggle";
import * as api from "../../services/api";
import type { Capability, Device, DeviceKind, DeviceStatus } from "../../services/types";

const CAPABILITY_LABELS: Record<Capability, string> = {
  ON: "Вкл",
  OFF: "Выкл",
  COOL: "Охлаждение",
  HEAT: "Нагрев",
  HUMIDIFY: "Увлажнение",
  DEHUMIDIFY: "Осушение",
};

const KIND_LABELS: Record<DeviceKind, string> = {
  LIGHT: "Свет",
  FAN: "Вентилятор",
  HUMIDIFIER: "Увлажнитель",
  DEHUMIDIFIER: "Осушитель",
  AIR_CONDITIONER: "Кондиционер",
  HEATER: "Обогреватель",
  OUTLET: "Розетка",
  OTHER: "Прочее",
};

const STATUS_LABELS: Record<DeviceStatus, string> = {
  OFF: "Выключено",
  ACTIVE: "Включено",
  COOLING: "Охлаждение",
  HEATING: "Нагрев",
  HUMIDIFYING: "Увлажнение",
  DEHUMIDIFYING: "Осушение",
  UNAVAILABLE: "Недоступно",
};

const STATUS_TONES: Record<DeviceStatus, "ok" | "warn" | "idle" | "bad"> = {
  OFF: "idle",
  ACTIVE: "ok",
  COOLING: "ok",
  HEATING: "ok",
  HUMIDIFYING: "ok",
  DEHUMIDIFYING: "ok",
  UNAVAILABLE: "bad",
};

interface DeviceCardProps {
  device: Device;
  title?: string;
  onError: (message: string) => void;
  onChanged: () => void;
}

/**
 * Рисует одно устройство и просит выполнить его способность.
 *
 * @param props.device Устройство со списком способностей и живым состоянием.
 * @param props.title Личный заголовок поверх имени устройства.
 * @param props.onError Вызывается с человеческим текстом отказа.
 * @param props.onChanged Вызывается после того, как что-то изменилось.
 */
export function DeviceCard({ device, title, onError, onChanged }: DeviceCardProps) {
  const unavailable = device.status === "UNAVAILABLE";
  const active = device.status !== "OFF" && !unavailable;
  const modes = device.capabilities.filter((capability) => capability !== "OFF");

  async function run(capability: Capability): Promise<void> {
    try {
      await api.performCapability(device.id, capability);
      onChanged();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Команда не выполнена");
    }
  }

  return (
    <article className={`device ${active ? "device--active" : ""}`.trim()}>
      <span className="device__glow" data-status={device.status} />

      <header className="device__head">
        <DeviceIcon kind={device.kind} active={active} />
        <div className="device__headline">
          <h3 className="device__name">{title ?? device.name}</h3>
          <p className="device__meta">
            {KIND_LABELS[device.kind]} · Канал {device.channel}
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
              aria-pressed={device.capabilities.includes(mode)}
              className={`chip ${device.status === modeToStatus(mode) ? "chip--active" : ""}`.trim()}
              disabled={unavailable}
              onClick={() => void run(mode)}
            >
              {CAPABILITY_LABELS[mode]}
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
          onChange={(next) => void run(next ? "ON" : "OFF")}
        />
      </div>
    </article>
  );
}

/**
 * Возвращает состояние, которого устройство ждёт от способности, чтобы подсветить
 * уже выбранный режим.
 *
 * @param capability Способность, которую карточка предлагает нажать.
 * @returns Состояние совпадения или None, когда сравнивать не с чем.
 */
function modeToStatus(capability: Capability): DeviceStatus | null {
  const statuses: Partial<Record<Capability, DeviceStatus>> = {
    ON: "ACTIVE",
    COOL: "COOLING",
    HEAT: "HEATING",
    HUMIDIFY: "HUMIDIFYING",
    DEHUMIDIFY: "DEHUMIDIFYING",
  };
  return statuses[capability] ?? null;
}
