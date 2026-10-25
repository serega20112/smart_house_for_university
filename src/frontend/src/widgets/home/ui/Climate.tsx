import "./climate.css";
/**
 * Климат дома: температура и влажность против целей автоматизации.
 *
 * Экран отвечает на один вопрос — далеко ли дому до того, что задал человек. Поэтому
 * крупно показывается измеренное значение, а под ним линейка с целью и допуском: без
 * числа пользователь гадал бы, много это или мало.
 *
 * Ничего не додумывается: пока датчик молчит, значения нет на экране, а не «0» и не
 * прошлое измерение, выданное за текущее.
 */

import { RangeBar } from "@/shared/ui";
import type { Automation, HomeState, Reading, TemperatureUnit } from "@/shared/api/types";

/** Насколько цель считается достигнутой: половина допуска уже «рядом». */
const NEAR_FACTOR = 0.5;

/**
 * Возвращает температуру в единице, которую выбрал аккаунт.
 *
 * @param celsius Значение в цельсиях, как его хранит сервер.
 * @param unit Единица показа.
 * @returns Число в выбранной единице.
 */
function convert(celsius: number, unit: TemperatureUnit): number {
  return unit === "C" ? celsius : celsius * 1.8 + 32;
}

/**
 * Возвращает словами, чем измеренное значение отличается от цели.
 *
 * @param value Измеренное значение в единице показа или None.
 * @param target Цель в той же единице.
 * @param tolerance Допуск в той же единице.
 * @param suffix Что дописать к числу: `°C` или `%`.
 * @returns Подпись и оттенок для значка отклонения.
 */
function measure(
  value: number | null,
  target: number,
  tolerance: number,
  suffix: string,
): { text: string; tone: string } {
  if (value === null) {
    return { text: "нет данных", tone: "idle" };
  }
  const offset = value - target;
  if (Math.abs(offset) <= tolerance * NEAR_FACTOR) {
    return { text: "у цели", tone: "ok" };
  }
  if (Math.abs(offset) <= tolerance) {
    return { text: "в допуске", tone: "ok" };
  }
  const direction = offset > 0 ? "выше" : "ниже";
  return { text: `${Math.abs(offset).toFixed(1)}${suffix} ${direction} цели`, tone: "warn" };
}

interface MetricProps {
  label: string;
  value: number | null;
  target: number;
  tolerance: number;
  suffix: string;
  step: number;
}

/**
 * Рисует один показатель климата: число, отклонение и линейку.
 *
 * @param props.label Что измеряем.
 * @param props.value Измеренное значение или None.
 * @param props.target Цель автоматизации в единице показа.
 * @param props.tolerance Допуск в единице показа.
 * @param props.suffix Единица, дописываемая к числу.
 * @param props.step Сколько знаков после запятой показывать.
 * @returns Разметка показателя.
 */
function Metric({ label, value, target, tolerance, suffix, step }: MetricProps) {
  const shown = value === null ? null : Number(value.toFixed(step));
  const deviation = measure(shown, Number(target.toFixed(step)), tolerance, suffix);
  const format = (item: number): string => `${item.toFixed(step)}${suffix}`;

  return (
    <div className="climate__metric">
      <div className="climate__metric-head">
        <span className="climate__label">{label}</span>
        <span className={`climate__tag climate__tag--${deviation.tone}`}>{deviation.text}</span>
      </div>
      <p className="climate__value num">
        {shown === null ? (
          <span className="climate__value--void">датчик молчит</span>
        ) : (
          <>
            {shown.toFixed(step)}
            <span className="climate__unit">{suffix}</span>
          </>
        )}
      </p>
      <RangeBar
        value={shown}
        target={Number(target.toFixed(step))}
        tolerance={tolerance}
        format={format}
      />
    </div>
  );
}

interface ClimateProps {
  state: HomeState;
  unit: TemperatureUnit;
  title: string;
}

/**
 * Возвращает панель климата: два показателя и заголовок.
 *
 * @param props.state Живой снимок дома.
 * @param props.unit Единица, в которой показывают температуру.
 * @param props.title Заголовок карточки.
 * @returns Разметка панели.
 */
export function Climate({ state, unit, title }: ClimateProps) {
  const automation: Automation = state.automation;
  const reading: Reading = state.reading;

  const temperature =
    reading.temperature === null
      ? null
      : convert(reading.temperature, unit);
  const targetTemperature = convert(automation.target_temperature, unit);
  const targetTolerance = unit === "C" ? automation.temperature_tolerance : automation.temperature_tolerance * 1.8;

  return (
    <section className="climate" aria-label={title}>
      <header className="climate__head">
        <h2 className="climate__title">{title}</h2>
        <p className="climate__note">
          {automation.enabled ? "Автоматика работает" : "Автоматика выключена"}
          {state.automation_suspended ? " · ручное управление" : ""}
        </p>
      </header>

      <div className="climate__grid">
        <Metric
          label="Температура"
          value={temperature}
          target={targetTemperature}
          tolerance={targetTolerance}
          suffix={unit === "C" ? "°C" : "°F"}
          step={1}
        />
        <Metric
          label="Влажность"
          value={reading.humidity}
          target={automation.target_humidity}
          tolerance={automation.humidity_tolerance}
          suffix="%"
          step={0}
        />
      </div>
    </section>
  );
}
