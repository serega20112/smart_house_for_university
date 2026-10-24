/**
 * Карточки климата: измеренные значения и то, к чему дом стремится.
 *
 * Числа приходят в градусах Цельсия и процентах, а пересчёт в выбранную человеком
 * единицу делает экран — бэкенд держит одно значение, чтобы его не пришлось
 * переводить обратно.
 */

import type { HomeState } from "../../services/types";

interface ClimateProps {
  state: HomeState;
  unit: "C" | "F";
}

/**
 * Пересчитывает температуру в единицу, которую выбрал человек.
 *
 * @param celsius Значение в градусах Цельсия.
 * @param unit Единица вывода.
 * @returns Температура в выбранной единице.
 */
function convert(celsius: number, unit: "C" | "F"): number {
  return unit === "F" ? celsius * 1.8 + 32 : celsius;
}

/**
 * Рисует измеренные значения климата в единице настроек аккаунта.
 *
 * @param props.state Живой снимок текущего аккаунта.
 * @param props.unit Единица температуры из сохранённых настроек.
 */
export function Climate({ state, unit }: ClimateProps) {
  const symbol = unit === "F" ? "°F" : "°C";
  const temperature = state.reading.temperature === null
    ? null
    : convert(state.reading.temperature, unit);
  const humidity = state.reading.humidity;
  const target = state.automation.target_temperature;
  const tolerance = state.automation.temperature_tolerance;
  const humidityTarget = state.automation.target_humidity;
  const humidityTolerance = state.automation.humidity_tolerance;

  return (
    <div className="grid grid--climate">
      <article className="metric-card">
        <span className="metric-card__ring" />
        <div className="metric-card__label">Температура</div>
        <p className="metric">
          {temperature === null ? "—" : temperature.toFixed(1)}
          {temperature !== null ? <span className="metric__unit">{symbol}</span> : null}
        </p>
        <p className="metric__note">
          цель {(target - tolerance).toFixed(1)}–
          {(target + tolerance).toFixed(1)}
          {symbol}
        </p>
      </article>

      <article className="metric-card metric-card--humidity">
        <span className="metric-card__ring" />
        <div className="metric-card__label">Влажность</div>
        <p className="metric">
          {humidity === null ? "—" : humidity.toFixed(0)}
          {humidity !== null ? <span className="metric__unit">%</span> : null}
        </p>
        <p className="metric__note">
          цель {(humidityTarget - humidityTolerance).toFixed(0)}–
          {(humidityTarget + humidityTolerance).toFixed(0)}%
        </p>
      </article>
    </div>
  );
}
