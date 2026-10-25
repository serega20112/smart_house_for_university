import "./editor.css";
/**
 * Форма устройства: имя, назначение, канал, способности и два признака участия.
 *
 * Способности человек выбирает сам, потому что сервер по ним решает, какие команды
 * устройству вообще можно ставить. Никаких догадок о железке: список каналов ограничен
 * шестью реле платы, а плата выбирается из тех, что уже сопряжены.
 */

import { useState, type FormEvent } from "react";

import * as api from "@/shared/api/client";
import { CAPABILITY_LABELS, CAPABILITY_ORDER, KIND_LABELS, KIND_ORDER } from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import { DeviceIcon, Toggle } from "@/shared/ui";
import type { Board, Capability, Device, DeviceKind } from "@/shared/api/types";

/** Первый канал реле и их число — столько же, сколько на плате. */
const CHANNELS = [1, 2, 3, 4, 5, 6];

/** Сколько символов выдерживает имя устройства. */
const NAME_MAX_LENGTH = 60;

interface DeviceEditorProps {
  /** Устройство, которое правят; None означает, что заводят новое. */
  device: Device | null;
  boards: Board[];
  /** Все устройства дома: по ним редактор показывает, какие каналы уже заняты. */
  devices: Device[];
  onSaved: () => void;
  onCancel: () => void;
}

/**
 * Возвращает редактор одного устройства.
 *
 * @param props.device Правится ли существующее устройство.
 * @param props.boards Платы аккаунта: выбор платы нужен, когда их больше одной.
 * @param props.devices Устройства дома — занятые каналы того же узла.
 * @param props.onSaved Вызывается после того, как сервер принял изменение.
 * @param props.onCancel Вызывается по кнопке отмены.
 */
export function DeviceEditor({ device, boards, devices, onSaved, onCancel }: DeviceEditorProps) {
  const singleBoard = boards.length <= 1;
  const initialBoard = device?.board_id ?? boards[0]?.id ?? "";

  // Устройство без указанной платы в доме с одной платой — то же самое, что на этой
  // плате, поэтому занятость канала считаем по всем устройствам выбранного узла.
  const takenChannels = (board: string): Map<number, string> =>
    new Map(
      devices
        .filter(
          (item) =>
            item.id !== device?.id &&
            (singleBoard || item.board_id === null || item.board_id === board),
        )
        .map((item) => [item.channel, item.name] as const),
    );

  const freeAtStart = CHANNELS.find((item) => !takenChannels(initialBoard).has(item)) ?? 1;

  const [name, setName] = useState(device?.name ?? "");
  const [kind, setKind] = useState<DeviceKind>(device?.kind ?? "LIGHT");
  const [channel, setChannel] = useState(device?.channel ?? freeAtStart);
  const [boardId, setBoardId] = useState(initialBoard);
  const [capabilities, setCapabilities] = useState<Capability[]>(
    device?.capabilities ?? ["ON", "OFF"],
  );
  const [enabled, setEnabled] = useState(device?.enabled ?? true);
  const [automationEnabled, setAutomationEnabled] = useState(device?.automation_enabled ?? true);
  const [busy, setBusy] = useState(false);

  const occupied = takenChannels(boardId);

  /**
   * Ставит или снимает способность из набора.
   *
   * @param capability Способность, по которой ударили.
   */
  function toggleCapability(capability: Capability): void {
    setCapabilities((current) =>
      current.includes(capability)
        ? current.filter((item) => item !== capability)
        : [...current, capability],
    );
  }

  /**
   * Отправляет форму: создаёт устройство или меняет существующее.
   *
   * @param event Событие отправки формы.
   */
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (name.trim().length === 0) {
      notify("Имя устройства пустое", "bad");
      return;
    }
    if (capabilities.length === 0) {
      notify("Не выбрано ни одной способности", "bad");
      return;
    }
    if (occupied.has(channel)) {
      notify(`Канал ${channel} занят устройством «${occupied.get(channel)}»`, "bad");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        name: name.trim(),
        kind,
        channel,
        capabilities,
        enabled,
        automation_enabled: automationEnabled,
        board_id: singleBoard ? null : boardId || null,
      };
      if (device) {
        await api.updateDevice(device.id, payload);
        notify(`${payload.name}: сохранено`, "ok");
      } else {
        await api.createDevice(payload);
        notify(`${payload.name}: устройство заведено`, "ok");
      }
      onSaved();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Устройство не сохранилось", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="editor" onSubmit={(event) => void submit(event)}>
      <header className="editor__head">
        <DeviceIcon kind={kind} active />
        <div>
          <h3 className="editor__title">{device ? "Правка устройства" : "Новое устройство"}</h3>
          <p className="editor__note">
            {device
              ? `Канал ${device.channel}, способности с сервера`
              : occupied.size >= CHANNELS.length
                ? "Свободных каналов на плате не осталось"
                : `Свободен канал ${freeAtStart}: одно реле — одно устройство`}
          </p>
        </div>
      </header>

      <label className="field">
        <span className="field__label">Имя</span>
        <input
          className="field__input"
          value={name}
          maxLength={NAME_MAX_LENGTH}
          placeholder="Как звать устройство"
          onChange={(event) => setName(event.target.value)}
        />
      </label>

      <div className="editor__pair">
        <label className="field">
          <span className="field__label">Назначение</span>
          <select value={kind} onChange={(event) => setKind(event.target.value as DeviceKind)}>
            {KIND_ORDER.map((item) => (
              <option key={item} value={item}>
                {KIND_LABELS[item]}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Канал</span>
          <select value={channel} onChange={(event) => setChannel(Number(event.target.value))}>
            {CHANNELS.map((item) => (
              <option key={item} value={item} disabled={occupied.has(item) && item !== device?.channel}>
                {occupied.has(item) && item !== device?.channel
                  ? `Канал ${item} — занят: ${occupied.get(item)}`
                  : `Канал ${item}`}
              </option>
            ))}
          </select>
        </label>
      </div>

      {!singleBoard ? (
        <label className="field">
          <span className="field__label">Плата</span>
          <select value={boardId} onChange={(event) => setBoardId(event.target.value)}>
            {boards.map((board) => (
              <option key={board.id} value={board.id}>
                {board.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <div className="field">
        <span className="field__label">Способности</span>
        <div className="chips">
          {CAPABILITY_ORDER.map((capability) => (
            <button
              key={capability}
              type="button"
              aria-pressed={capabilities.includes(capability)}
              className={`chip ${capabilities.includes(capability) ? "chip--active" : ""}`.trim()}
              onClick={() => toggleCapability(capability)}
            >
              {CAPABILITY_LABELS[capability]}
            </button>
          ))}
        </div>
      </div>

      <div className="editor__switches">
        <div className="switch-row">
          <div>
            <p className="switch-row__title">Управление разрешено</p>
            <p className="switch-row__note">Снимите, чтобы устройство не участвовало в командах словами</p>
          </div>
          <Toggle checked={enabled} label="Управление разрешено" onChange={setEnabled} />
        </div>

        <div className="switch-row">
          <div>
            <p className="switch-row__title">Участие в автоматизации</p>
            <p className="switch-row__note">Автоматика трогает только такие устройства</p>
          </div>
          <Toggle
            checked={automationEnabled}
            label="Участие в автоматизации"
            onChange={setAutomationEnabled}
          />
        </div>
      </div>

      <footer className="editor__foot">
        {device ? (
          <button
            type="button"
            className="button button--danger"
            disabled={busy}
            onClick={() => {
              if (!window.confirm(`Удалить «${device.name}»?`)) {
                return;
              }
              setBusy(true);
              void api
                .deleteDevice(device.id)
                .then(() => {
                  notify(`${device.name}: удалено`, "ok");
                  onSaved();
                })
                .catch((exc: unknown) => {
                  notify(exc instanceof Error ? exc.message : "Устройство не удалилось", "bad");
                })
                .finally(() => setBusy(false));
            }}
          >
            Удалить
          </button>
        ) : (
          <button type="button" className="button button--ghost" disabled={busy} onClick={onCancel}>
            Отмена
          </button>
        )}
        <button className="button button--primary" type="submit" disabled={busy}>
          {busy ? "Сохраняю…" : "Сохранить"}
        </button>
      </footer>
    </form>
  );
}
