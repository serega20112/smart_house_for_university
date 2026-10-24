/**
 * Редактор одного устройства со страницы устройств.
 *
 * Форма собирает частичное изменение и отправляет его целиком в одну команду:
 * какие сочетания способностей и каналов допустимы, решает домен, а не проверка
 * на экране, поэтому здесь отказ сервера только показывается.
 */

import { useEffect, useState } from "react";

import * as api from "../../services/api";
import type { Capability, Device, DeviceKind } from "../../services/types";

const KINDS: DeviceKind[] = [
  "LIGHT",
  "FAN",
  "HUMIDIFIER",
  "DEHUMIDIFIER",
  "AIR_CONDITIONER",
  "HEATER",
  "OUTLET",
  "OTHER",
];

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

const CAPABILITIES: { value: Capability; label: string }[] = [
  { value: "ON", label: "Включение" },
  { value: "OFF", label: "Выключение" },
  { value: "COOL", label: "Охлаждение" },
  { value: "HEAT", label: "Нагрев" },
];

const CHANNELS = [1, 2, 3, 4, 5, 6];

interface Draft {
  name: string;
  kind: DeviceKind;
  channel: number;
  capabilities: Capability[];
  enabled: boolean;
  automationEnabled: boolean;
}

interface DeviceEditorProps {
  device: Device;
  takenChannels: number[];
  onSaved: () => void;
  onError: (message: string) => void;
}

function draftOf(device: Device): Draft {
  return {
    name: device.name,
    kind: device.kind,
    channel: device.channel,
    capabilities: [...device.capabilities],
    enabled: device.enabled,
    automationEnabled: device.automation_enabled,
  };
}

export function DeviceEditor({
  device,
  takenChannels,
  onSaved,
  onError,
}: DeviceEditorProps) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(device));

  useEffect(() => {
    setDraft(draftOf(device));
  }, [device.id]);

  function patch(next: Partial<Draft>): void {
    setDraft((current) => ({ ...current, ...next }));
  }

  function toggle(capability: Capability): void {
    patch({
      capabilities: draft.capabilities.includes(capability)
        ? draft.capabilities.filter((item) => item !== capability)
        : [...draft.capabilities, capability],
    });
  }

  async function save(): Promise<void> {
    try {
      await api.updateDevice(device.id, {
        name: draft.name,
        kind: draft.kind,
        channel: draft.channel,
        capabilities: draft.capabilities,
        enabled: draft.enabled,
        automation_enabled: draft.automationEnabled,
      });
      onSaved();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Не удалось сохранить устройство");
    }
  }

  async function remove(): Promise<void> {
    try {
      await api.deleteDevice(device.id);
      onSaved();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Не удалось удалить устройство");
    }
  }

  const dirty =
    draft.name !== device.name ||
    draft.kind !== device.kind ||
    draft.channel !== device.channel ||
    draft.enabled !== device.enabled ||
    draft.automationEnabled !== device.automation_enabled ||
    draft.capabilities.length !== device.capabilities.length ||
    draft.capabilities.some((item) => !device.capabilities.includes(item));

  return (
    <article className="editor">
      <header className="editor__head">
        <h3 className="editor__title">{device.name}</h3>
        <span className={`editor__dot editor__dot--${device.status.toLowerCase()}`} />
      </header>

      <label className="field">
        <span>Название</span>
        <input
          value={draft.name}
          onChange={(event) => patch({ name: event.target.value })}
        />
      </label>

      <label className="field">
        <span>Назначение</span>
        <select
          value={draft.kind}
          onChange={(event) => patch({ kind: event.target.value as DeviceKind })}
        >
          {KINDS.map((item) => (
            <option key={item} value={item}>
              {KIND_LABELS[item]}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Канал реле</span>
        <select
          value={draft.channel}
          onChange={(event) => patch({ channel: Number(event.target.value) })}
        >
          {CHANNELS.map((item) => {
            const taken = takenChannels.includes(item) && item !== device.channel;
            return (
              <option key={item} value={item} disabled={taken}>
                Канал {item}
                {taken ? " — занят" : ""}
              </option>
            );
          })}
        </select>
      </label>

      <div className="field">
        <span>Возможности</span>
        <div className="chips">
          {CAPABILITIES.map(({ value, label }) => {
            const active = draft.capabilities.includes(value);
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                className={`chip ${active ? "chip--active" : ""}`.trim()}
                onClick={() => toggle(value)}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={draft.enabled}
          onChange={(event) => patch({ enabled: event.target.checked })}
        />
        <span>Устройство включено</span>
      </label>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={draft.automationEnabled}
          onChange={(event) => patch({ automationEnabled: event.target.checked })}
        />
        <span>Участвует в автоматизации</span>
      </label>

      <div className="editor__actions">
        <button
          className="button button--primary"
          type="button"
          disabled={!dirty}
          onClick={() => void save()}
        >
          Сохранить
        </button>
        <button className="button button--ghost" type="button" onClick={() => void remove()}>
          Удалить
        </button>
      </div>
    </article>
  );
}
