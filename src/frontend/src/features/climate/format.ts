/** Время и климатические значения, отформатированные для карточек. */

export function formatTemperature(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(1)}°C`;
}

export function formatHumidity(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(0)}%`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMoment(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
