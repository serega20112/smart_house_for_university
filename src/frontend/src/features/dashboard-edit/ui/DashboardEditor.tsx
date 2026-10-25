import "./dashboard-editor.css";
/**
 * Сборка главного экрана.
 *
 * Раскладка принадлежит аккаунту, а не сборке: сервер хранит список виджетов, экран его
 * рисует. Здесь человек решает, какие карточки видеть, в каком порядке и под какими
 * личными заголовками. Порядок меняется стрелками: перетаскивание на списке из шести
 * строк выглядит удобнее, пока не попробуешь его на телефоне.
 */

import { useState } from "react";

import * as api from "@/shared/api/client";
import { WIDGET_LABELS } from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import type { Device, Widget, WidgetType } from "@/shared/api/types";

/** Виджеты, которые добавляются одним нажатием; плитку устройства выбирают отдельно. */
const QUICK_ADDS: readonly WidgetType[] = ["climate", "sensor", "command"];

/** Раскладка по умолчанию: тот же набор, что рисует Dashboard без сохранённых виджетов. */
const DEFAULT_LAYOUT: Widget[] = [
  { type: "climate", device_id: null, title: "Климат" },
  { type: "command", device_id: null, title: "Команды" },
];

/** Знаки порядка: стрелки и крестик рисуются здесь же, они нужны только этой форме. */
const ICONS: Record<string, JSX.Element> = {
  up: <path d="M12 19V5M6 11l6-6 6 6" />,
  down: <path d="M12 5v14M6 13l6 6 6-6" />,
  remove: <path d="M6 6l12 12M18 6L6 18" />,
};

/** Строка списка: виджет плюс устойчивый ключ, чтобы перестановка не путала ввод. */
type Row = Widget & { key: number };

/** Ключи строк: порядок важнее содержимого, поэтому номер просто следующий. */
let nextKey = 0;

interface DashboardEditorProps {
  widgets: Widget[];
  devices: Device[];
  onSaved: () => void;
  onCancel: () => void;
}

/**
 * Возвращает редактор раскладки главного экрана.
 *
 * @param props.widgets Раскладка, пришедшая с сервера.
 * @param props.devices Устройства, которыми можно питают плитку.
 * @param props.onSaved Вызывается, когда новая раскладка сохранена.
 * @param props.onCancel Вызывается по кнопке отмены.
 */
export function DashboardEditor({ widgets, devices, onSaved, onCancel }: DashboardEditorProps) {
  const source = widgets.length > 0 ? widgets : DEFAULT_LAYOUT;
  const [rows, setRows] = useState<Row[]>(() =>
    source.map((widget) => ({ ...widget, key: nextKey++ })),
  );
  const [picked, setPicked] = useState(devices[0]?.id ?? "");
  const [busy, setBusy] = useState(false);

  /**
   * Меняет местами две соседние строки.
   *
   * @param index Строка, которую двигают.
   * @param step Куда: -1 вверх, 1 вниз.
   */
  function move(index: number, step: number): void {
    const target = index + step;
    if (target < 0 || target >= rows.length) {
      return;
    }
    setRows((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  /**
   * Меняет строку.
   *
   * @param index Номер строки.
   * @param changes Поля, которые подставляются.
   */
  function patch(index: number, changes: Partial<Widget>): void {
    setRows((current) =>
      current.map((row, position) => (position === index ? { ...row, ...changes } : row)),
    );
  }

  /**
   * Добавляет строку в конец списка.
   *
   * @param type Вид карточки.
   * @param deviceId Устройство для плитки; для остальных видов None.
   */
  function add(type: WidgetType, deviceId: string | null = null): void {
    setRows((current) => [...current, { type, device_id: deviceId, title: null, key: nextKey++ }]);
  }

  /**
   * Сохраняет раскладку на сервере.
   */
  async function save(): Promise<void> {
    setBusy(true);
    try {
      await api.updateDashboard(rows.map(({ type, device_id, title }) => ({ type, device_id, title })));
      notify("Главный экран сохранён", "ok");
      onSaved();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Раскладка не сохранилась", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="layout-editor">
      <header className="layout-editor__head">
        <h2 className="layout-editor__title">Что видно на главном экране</h2>
        <p className="layout-editor__note">Порядок сверху вниз; пустой заголовок — имя по умолчанию.</p>
      </header>

      <ul className="layout-editor__rows">
        {rows.map((row, index) => (
          <li key={row.key} className="layout-editor__row">
            <span className="layout-editor__kind">{WIDGET_LABELS[row.type]}</span>

            {row.type === "device" ? (
              <select
                className="layout-editor__device"
                value={row.device_id ?? ""}
                onChange={(event) => patch(index, { device_id: event.target.value })}
              >
                {devices.map((device) => (
                  <option key={device.id} value={device.id}>
                    {device.name}
                  </option>
                ))}
              </select>
            ) : null}

            <input
              className="layout-editor__name"
              placeholder="Заголовок"
              value={row.title ?? ""}
              onChange={(event) =>
                patch(index, { title: event.target.value.trim() === "" ? null : event.target.value })
              }
            />

            <span className="layout-editor__moves">
              <button
                type="button"
                className="icon-button"
                aria-label="Выше"
                disabled={index === 0}
                onClick={() => move(index, -1)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  {ICONS.up}
                </svg>
              </button>
              <button
                type="button"
                className="icon-button"
                aria-label="Ниже"
                disabled={index === rows.length - 1}
                onClick={() => move(index, 1)}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  {ICONS.down}
                </svg>
              </button>
              <button
                type="button"
                className="icon-button"
                aria-label="Убрать с экрана"
                onClick={() => setRows((current) => current.filter((_, position) => position !== index))}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
                  {ICONS.remove}
                </svg>
              </button>
            </span>
          </li>
        ))}
        {rows.length === 0 ? <li className="layout-editor__empty">Экран пуст.</li> : null}
      </ul>

      <div className="layout-editor__add">
        {QUICK_ADDS.map((type) => (
          <button key={type} type="button" className="chip" onClick={() => add(type)}>
            + {WIDGET_LABELS[type]}
          </button>
        ))}

        {devices.length > 0 ? (
          <>
            <select
              className="layout-editor__device"
              value={picked}
              onChange={(event) => setPicked(event.target.value)}
            >
              {devices.map((device) => (
                <option key={device.id} value={device.id}>
                  {device.name}
                </option>
              ))}
            </select>
            <button type="button" className="chip" onClick={() => add("device", picked)}>
              + Плитка устройства
            </button>
          </>
        ) : null}
      </div>

      <footer className="layout-editor__foot">
        <button type="button" className="button button--ghost" disabled={busy} onClick={onCancel}>
          Отмена
        </button>
        <button type="button" className="button button--primary" disabled={busy} onClick={() => void save()}>
          {busy ? "Сохраняю…" : "Сохранить экран"}
        </button>
      </footer>
    </div>
  );
}
