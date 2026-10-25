import "./devices.css";
/**
 * Экран устройств.
 *
 * Это мастерская, а не витрина: здесь настраивают, какой канал реле чем считается,
 * какие способности у устройства есть и участвует ли оно в автоматике и командах.
 * Живым состоянием дом занимается на главном экране.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { DeviceEditor } from "@/features/device-edit";
import { useHomeState } from "@/entities/home";
import * as api from "@/shared/api/client";
import { KIND_LABELS, STATUS_LABELS, isDeviceActive, statusTone } from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import type { Board, Device, DeviceKind } from "@/shared/api/types";
import { Badge, DeviceIcon } from "@/shared/ui";

export function DevicesPage() {
  const { state, error, refresh } = useHomeState();
  const [boards, setBoards] = useState<Board[]>([]);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<DeviceKind | "ALL">("ALL");
  const [editing, setEditing] = useState<Device | null>(null);
  const [creating, setCreating] = useState(false);

  /**
   * Читает платы: редактору нужен список, куда денется канал нового устройства.
   */
  const loadBoards = useCallback(async () => {
    try {
      setBoards(await api.fetchBoards());
    } catch {
      setBoards([]);
    }
  }, []);

  useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  const devices = state?.devices ?? [];

  // Виды, которые действительно встречаются: чипов «на всякий случай» не показываем.
  const kinds = useMemo(
    () => Array.from(new Set(devices.map((device) => device.kind))),
    [devices],
  );

  const visible = devices.filter((device) => {
    const byKind = kind === "ALL" || device.kind === kind;
    const text = query.trim().toLowerCase();
    const byQuery =
      text.length === 0 ||
      device.name.toLowerCase().includes(text) ||
      KIND_LABELS[device.kind].toLowerCase().includes(text);
    return byKind && byQuery;
  });

  /**
   * Закрывает форму и перечитывает список с устройствами.
   */
  async function finish(): Promise<void> {
    setEditing(null);
    setCreating(false);
    await refresh();
    void loadBoards();
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <p className="page__eyebrow">Настройка</p>
          <h1 className="page__title">Устройства</h1>
          <p className="page__subtitle">
            Логические устройства поверх каналов реле платы; {devices.length} всего,
            {" "}{devices.filter((device) => device.automation_enabled).length} в автоматике
          </p>
        </div>
        <button
          type="button"
          className="button button--primary"
          onClick={() => {
            setEditing(null);
            setCreating(true);
          }}
        >
          Добавить устройство
        </button>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      {creating || editing ? (
        <DeviceEditor
          device={editing}
          boards={boards}
          devices={devices}
          onSaved={() => void finish()}
          onCancel={() => {
            setCreating(false);
            setEditing(null);
          }}
        />
      ) : null}

      <div className="devices__toolbar">
        <label className="field field--search devices__search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
            <circle cx="11" cy="11" r="6" />
            <path d="m20 20-4.5-4.5" />
          </svg>
          <input
            className="field__input"
            value={query}
            placeholder="Имя или назначение"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>

        <div className="chips">
          <button
            type="button"
            className={`chip ${kind === "ALL" ? "chip--active" : ""}`.trim()}
            onClick={() => setKind("ALL")}
          >
            Все
          </button>
          {kinds.map((item) => (
            <button
              key={item}
              type="button"
              className={`chip ${kind === item ? "chip--active" : ""}`.trim()}
              onClick={() => setKind(item)}
            >
              {KIND_LABELS[item]}
            </button>
          ))}
        </div>
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          <p className="empty__title">
            {devices.length === 0 ? "Устройств пока нет" : "Под фильтр ничего не попало"}
          </p>
          <p>
            {devices.length === 0
              ? "Заведите устройство: канал реле, назначение и способности."
              : "Смените слово или снимите фильтр по назначению."}
          </p>
        </div>
      ) : (
        <ul className="devices">
          {visible.map((device) => (
            <li key={device.id} className={`device-row device-row--${statusTone(device.status)}`}>
              <DeviceIcon kind={device.kind} active={isDeviceActive(device.status)} />

              <div className="device-row__main">
                <p className="device-row__name">{device.name}</p>
                <p className="device-row__note">
                  {KIND_LABELS[device.kind]} · канал {device.channel}
                  {device.board_id
                    ? ` · ${boards.find((board) => board.id === device.board_id)?.name ?? "плата"}`
                    : ""}
                </p>
              </div>

              <div className="device-row__flags">
                <Badge
                  tone={device.enabled ? "ok" : "idle"}
                  label={device.enabled ? "Команды" : "Команды закрыты"}
                />
                <Badge
                  tone={device.automation_enabled ? "ok" : "idle"}
                  label={device.automation_enabled ? "Автоматика" : "Вне автоматики"}
                />
              </div>

              <span className="device-row__status">
                <Badge tone={statusTone(device.status)} label={STATUS_LABELS[device.status]} />
              </span>

              <button
                type="button"
                className="button"
                onClick={() => {
                  setCreating(false);
                  setEditing(device);
                  notify(`Правка: ${device.name}`, "info");
                }}
              >
                Править
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
