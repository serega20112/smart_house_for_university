import "./device-icon.css";
/**
 * Значок назначения устройства.
 *
 * Форма рисует назначение, а не украшение: по силуэту человек находит нужную плитку
 * быстрее, чем по подписи. Знаки рисованы кодом — ни одной принесённой картинки, ни
 * одного лишнего запроса в сборке, зато цвет берётся из состояния устройства.
 */

import type { DeviceKind } from "@/shared/api/types";

/** Контур значка: набор путей, которые рисуют один силуэт. */
const SHAPES: Record<DeviceKind, JSX.Element> = {
  LIGHT: (
    <>
      <path d="M9 17h6" />
      <path d="M10 20h4" />
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5.9 1.1.9 1.8h5.2c0-.7.3-1.3.9-1.8A6 6 0 0 0 12 3Z" />
    </>
  ),
  FAN: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="1.6" />
      <path d="M12 3.5c2.4 1.6 3.4 4 3 6.4M20.5 12c-1.6 2.4-4 3.4-6.4 3M12 20.5c-2.4-1.6-3.4-4-3-6.4" />
    </>
  ),
  HUMIDIFIER: (
    <>
      <path d="M12 3.5c2.8 3.4 4.5 5.8 4.5 8a4.5 4.5 0 1 1-9 0c0-2.2 1.7-4.6 4.5-8Z" />
      <path d="M6 19.5c1.6.9 3.6.9 5.4 0 1.8-.9 3.8-.9 5.6 0" />
    </>
  ),
  DEHUMIDIFIER: (
    <>
      <path d="M12 4c2.6 3.2 4.2 5.4 4.2 7.4a4.2 4.2 0 1 1-8.4 0C7.8 9.4 9.4 7.2 12 4Z" />
      <path d="M5 19l14-14" />
    </>
  ),
  AIR_CONDITIONER: (
    <>
      <path d="M12 3v18M4.2 7.5l15.6 9M19.8 7.5l-15.6 9" />
      <path d="M12 6.4 10 4.6M12 6.4l2-1.8M12 17.6l-2 1.8M12 17.6l2 1.8" />
    </>
  ),
  HEATER: (
    <>
      <path d="M12 3c1.2 3 3.6 4.2 4.8 6.6a5.4 5.4 0 1 1-9.6 0C5 9.6 6.4 8.4 7.4 6.6" />
      <path d="M9.6 19.5h4.8" />
    </>
  ),
  OUTLET: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="M10 9.5v3M14 9.5v3" />
      <path d="M12 15.5v.01" />
    </>
  ),
  OTHER: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="4" />
      <path d="M9 12h6" />
    </>
  ),
};

interface DeviceIconProps {
  kind: DeviceKind;
  /** Активная плитка красит значок акцентом: свет горит — знак горит. */
  active?: boolean;
}

/**
 * Возвращает силуэт назначения устройства.
 *
 * @param props.kind Назначение, пришедшее с сервера.
 * @param props.active Занимается ли устройство чем-то сейчас.
 * @returns Разметка значка.
 */
export function DeviceIcon({ kind, active = false }: DeviceIconProps) {
  return (
    <span className={`device-icon ${active ? "device-icon--active" : ""}`.trim()} aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {SHAPES[kind] ?? SHAPES.OTHER}
      </svg>
    </span>
  );
}
