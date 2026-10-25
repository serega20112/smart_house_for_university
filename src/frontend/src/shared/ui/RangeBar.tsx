import "./range-bar.css";
/**
 * Линейка климата: где цель, где допуск и где оказался дом.
 *
 * Одного числа на экране мало: человек смотрит не «сколько градусов», а «далеко ли до
 * цели и в какую сторону». Полоса рисует и то, и другое — диапазон, в котором дом уже
 * считается комфортным, и точку текущего значения.
 *
 * Ничего не выдумывается: если измерения нет, точка не появляется, а полоса остаётся
 * пустой шкалой.
 */

import type { Tone } from "@/shared/lib/labels";

/** Оттенок точки на шкале: шире, чем тон пилюли, потому что важен знак отклонения. */
type MarkerTone = Tone | "warm" | "cool";

/** Сколько половины диапазона показывать за пределами допуска, когда данных мало. */
const SPAN_FACTORS = 3;

/** Запас по краям шкалы, чтобы точка не липла к границе. */
const EDGE_FACTOR = 0.15;

interface RangeBarProps {
  value: number | null;
  target: number;
  tolerance: number;
  format: (value: number) => string;
}

/**
 * Возвращает процент позиции числа на шкале.
 *
 * @param value Искомое число.
 * @param from Начало шкалы.
 * @param to Конец шкалы.
 * @returns Позиция в процентах, зажатая в границы шкалы.
 */
function toPercent(value: number, from: number, to: number): number {
  if (to === from) {
    return 50;
  }
  const ratio = ((value - from) / (to - from)) * 100;
  return Math.min(100, Math.max(0, ratio));
}

/** Чем красить точку: ниже цели дом недогревает, выше — перегревает. */
function markerTone(offset: number | null, tolerance: number): MarkerTone {
  if (offset === null) {
    return "idle";
  }
  if (Math.abs(offset) <= tolerance) {
    return "ok";
  }
  return offset > 0 ? "warm" : "cool";
}

/**
 * Рисует шкалу с допуском вокруг цели и текущим значением.
 *
 * @param props.value Измеренное значение или None, когда датчик молчит.
 * @param props.target Цель, к которой дом стремится.
 * @param props.tolerance Допуск: внутри него значение считается нормой.
 * @param props.format Как показывать числа этой шкалы.
 * @returns Разметка полосы.
 */
export function RangeBar({ value, target, tolerance, format }: RangeBarProps) {
  const span = Math.max(tolerance * SPAN_FACTORS, 1);
  const from = Math.min(target - span, value ?? target - span);
  const to = Math.max(target + span, value ?? target + span);
  const pad = (to - from) * EDGE_FACTOR || 1;
  const lo = from - pad;
  const hi = to + pad;

  const offset = value === null ? null : value - target;
  const tone = markerTone(offset, tolerance);

  return (
    <div className="range-bar">
      <div className="range-bar__track">
        <span
          className="range-bar__band"
          style={{
            left: `${toPercent(target - tolerance, lo, hi)}%`,
            width: `${toPercent(target + tolerance, lo, hi) - toPercent(target - tolerance, lo, hi)}%`,
          }}
        />
        <span className="range-bar__target" style={{ left: `${toPercent(target, lo, hi)}%` }} />
        {value !== null ? (
          <span
            className={`range-bar__marker range-bar__marker--${tone}`}
            style={{ left: `${toPercent(value, lo, hi)}%` }}
            title={format(value)}
          />
        ) : null}
      </div>
      <div className="range-bar__scale">
        <span>{format(lo)}</span>
        <span className="range-bar__scale-center">
          цель {format(target)}, допуск ±{format(tolerance)}
        </span>
        <span>{format(hi)}</span>
      </div>
    </div>
  );
}
