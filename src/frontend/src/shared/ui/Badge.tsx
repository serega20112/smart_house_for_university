import "./badge.css";
/**
 * Пилюля статуса.
 *
 * Один значок на весь интерфейс: оттенок берётся из состояния, а не из настроения
 * того среза, который его рисует. Иначе «работает» на одном экране зелёный, на другом
 * — синий, и человеку приходится сверять.
 */

import type { Tone } from "@/shared/lib/labels";

interface BadgeProps {
  tone: Tone;
  label: string;
}

/**
 * Возвращает состояние короткой подписью с цветной точкой.
 *
 * @param props.tone Оттенок, который привязан к смыслу состояния.
 * @param props.label Подпись, которую читает человек.
 * @returns Разметка пилюли.
 */
export function Badge({ tone, label }: BadgeProps) {
  return (
    <span className={`badge badge--${tone}`}>
      <span className="badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
