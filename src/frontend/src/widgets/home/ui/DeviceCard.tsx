import "./device.css";
/**
 * Плитка устройства.
 *
 * Плитка показывает, что устройство делает сейчас, и даёт одно главное действие —
 * включить или выключить. Остальные способности прячутся в ряд chips: они нужны редко,
 * но прятать их под меню означало бы тыкать в плитку каждый раз.
 *
 * Никаких выдуманных состояний: если сервер сказал «нет связи», тумблер не перещёлкивает
 * устройство в «выключено», а честно сообщает, что команды не уходят.
 */

import { useState } from "react";

import * as api from "@/shared/api/client";
import {
  CAPABILITY_DONE_LABELS,
  CAPABILITY_LABELS,
  STATUS_LABELS,
  isDeviceActive,
  statusTone,
} from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import { DeviceIcon, Toggle } from "@/shared/ui";
import type { Capability, Device } from "@/shared/api/types";

interface DeviceCardProps {
  device: Device;
  title?: string;
  /** Плата, на которой стоит канал; None, когда платы не видно. */
  boardName?: string;
  onChanged: () => void;
}

/**
 * Возвращает плитку одного устройства.
 *
 * @param props.device Устройство со снимка дома.
 * @param props.title Личный заголовок из раскладки вместо имени устройства.
 * @param props.boardName Плата, которой принадлежит канал.
 * @param props.onChanged Вызывается после того, как команда ушла на сервер.
 * @returns Разметка плитки.
 */
export function DeviceCard({ device, title, boardName, onChanged }: DeviceCardProps) {
  const [busy, setBusy] = useState(false);
  const active = isDeviceActive(device.status);
  const tone = statusTone(device.status);

  /**
   * Просит устройство выполнить способность и сообщает результат.
   *
   * @param capability Способность из перечня устройства.
   */
  async function apply(capability: Capability): Promise<void> {
    setBusy(true);
    try {
      await api.performCapability(device.id, capability);
      notify(`${title ?? device.name}: ${CAPABILITY_DONE_LABELS[capability]}`, "ok");
      onChanged();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Команда не ушла", "bad");
    } finally {
      setBusy(false);
    }
  }

  // Способности кроме включения-выключения: они есть у климата и не нужны свету.
  const extras = device.capabilities.filter((item) => item !== "ON" && item !== "OFF");
  const controllable = device.status !== "UNAVAILABLE";

  return (
    <article className={`device device--${tone}`}>
      <header className="device__head">
        <DeviceIcon kind={device.kind} active={active} />
        <div className="device__titles">
          <h3 className="device__name">{title ?? device.name}</h3>
          <p className="device__note">
            канал {device.channel}
            {boardName ? ` · ${boardName}` : ""}
            {!device.enabled ? " · исключено из команд" : !device.automation_enabled ? " · вне автоматики" : ""}
          </p>
        </div>
      </header>

      <footer className="device__foot">
        <span className={`device__state device__state--${tone}`}>{STATUS_LABELS[device.status]}</span>
        <Toggle
          checked={active}
          disabled={busy || !controllable}
          label={`${STATUS_LABELS[device.status]}: ${device.name}`}
          onChange={(next) => void apply(next ? "ON" : "OFF")}
        />
      </footer>

      {extras.length > 0 ? (
        <div className="chips device__extra">
          {extras.map((capability) => (
            <button
              key={capability}
              type="button"
              className="chip"
              disabled={busy || !controllable}
              onClick={() => void apply(capability)}
            >
              {CAPABILITY_LABELS[capability]}
            </button>
          ))}
        </div>
      ) : null}
    </article>
  );
}
