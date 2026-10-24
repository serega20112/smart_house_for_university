/** Значки устройств: их рисует код, а не принесённые картинки. */

import type { DeviceKind } from "../services/types";

interface IconProps {
  kind: DeviceKind;
  active: boolean;
}

const PATHS: Record<DeviceKind, JSX.Element> = {
  LIGHT: (
    <>
      <path d="M9 18h6M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.5.4.8 1 .8 1.6V16h5.4v-.5c0-.6.3-1.2.8-1.6A6 6 0 0 0 12 3Z" />
    </>
  ),
  FAN: (
    <>
      <circle cx="12" cy="12" r="2" />
      <path d="M12 10c0-3 1-5 3-5s3 2 2 4-3 3-5 1Z" />
      <path d="M14 12c3 0 5 1 5 3s-2 3-4 2-3-3-1-5Z" />
      <path d="M12 14c0 3-1 5-3 5s-3-2-2-4 3-3 5-1Z" />
    </>
  ),
  HUMIDIFIER: (
    <>
      <path d="M12 3s5 5.5 5 9a5 5 0 0 1-10 0c0-3.5 5-9 5-9Z" />
      <path d="M9.5 14a2.5 2.5 0 0 0 2.5 2.5" />
    </>
  ),
  DEHUMIDIFIER: (
    <>
      <path d="M12 21s-5-5.5-5-9a5 5 0 0 1 10 0c0 3.5-5 9-5 9Z" />
      <path d="M8 5h8M10 3v4M14 3v4" />
    </>
  ),
  AIR_CONDITIONER: (
    <>
      <rect x="3" y="5" width="18" height="8" rx="2" />
      <path d="M7 17v2M11 17v3M15 17v2M19 17v3" />
    </>
  ),
  HEATER: (
    <>
      <rect x="5" y="4" width="14" height="16" rx="2" />
      <path d="M9 8c0 1.5 1 2 1 3.5S9 13.5 9 15M13 8c0 1.5 1 2 1 3.5S13 13.5 13 15" />
    </>
  ),
  OUTLET: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M9 10h.01M15 10h.01M10 14v2M14 14v2" />
    </>
  ),
  OTHER: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="3" />
      <path d="M12 9v6M9 12h6" />
    </>
  ),
};

/**
 * Возвращает значок назначения устройства.
 *
 * @param props.kind Назначение устройства.
 * @param props.active Нужно ли подсветить значок включённым состоянием.
 */
export function DeviceIcon({ kind, active }: IconProps) {
  return (
    <span className={`device__icon ${active ? "device__icon--active" : ""}`.trim()}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        {PATHS[kind] ?? PATHS.OTHER}
      </svg>
    </span>
  );
}
