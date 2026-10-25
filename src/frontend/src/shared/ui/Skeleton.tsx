import "./skeleton.css";
/**
 * Заготовка вместо содержимого, которого ещё нет.
 *
 * Экран не должен подпрыгивать, когда приедут числа: заготовка повторяет форму
 * настоящего блока — плитки устройств или полос климата — и держит место до ответа.
 */

/** Форма заготовки: что она изображает. */
export type SkeletonVariant = "tiles" | "rows" | "climate";

/** Столько же плиток, сколько успевает уместиться в ряд на типовом экране. */
const TILES = 4;

/** Столько же строк, сколько показывает список плат или сценариев. */
const ROWS = 3;

interface SkeletonProps {
  variant?: SkeletonVariant;
  count?: number;
}

/**
 * Возвращает набор пустых блоков нужной формы.
 *
 * @param props.variant Форма: плитки, строки списка или полоса климата.
 * @param props.count Сколько строк рисовать, когда форма — список.
 * @returns Разметка заготовки.
 */
export function Skeleton({ variant = "tiles", count }: SkeletonProps) {
  if (variant === "climate") {
    return (
      <div className="skeleton skeleton--climate" aria-hidden="true">
        <span className="skeleton__block skeleton__block--value" />
        <span className="skeleton__block skeleton__block--bar" />
        <span className="skeleton__block skeleton__block--line" />
      </div>
    );
  }

  if (variant === "rows") {
    const total = count ?? ROWS;
    return (
      <div className="skeleton skeleton--rows" aria-hidden="true">
        {Array.from({ length: total }, (_, index) => index).map((row) => (
          <span key={row} className="skeleton__block skeleton__block--row" />
        ))}
      </div>
    );
  }

  return (
    <div className="skeleton skeleton--tiles" aria-hidden="true">
      {Array.from({ length: TILES }, (_, index) => index).map((tile) => (
        <span key={tile} className="skeleton__block" />
      ))}
    </div>
  );
}
