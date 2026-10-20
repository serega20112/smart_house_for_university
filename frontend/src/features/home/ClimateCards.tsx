/** Climate cards with the current temperature and humidity. */

import type { HomeState } from "../../services/types";

interface ClimateProps {
  state: HomeState;
  unit: string;
}

function convert(celsius: number, unit: string): number {
  return unit === "F" ? celsius * 1.8 + 32 : celsius;
}

/**
 * Renders the measured climate values in the unit the account prefers.
 *
 * @param props.state Live snapshot of the current account.
 * @param props.unit Temperature unit stored in the preferences.
 */
export function Climate({ state, unit }: ClimateProps) {
  const symbol = unit === "F" ? "°F" : "°C";
  const temperature =
    state.temperature === null ? null : convert(state.temperature, unit);
  const humidity = state.humidity;
  const targetTemperature = convert(state.automation.target_temperature, unit);

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
          цель {targetTemperature.toFixed(1)}
          {symbol} · {convert(state.automation.min_temperature, unit).toFixed(1)}–
          {convert(state.automation.max_temperature, unit).toFixed(1)}
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
          цель {state.automation.target_humidity.toFixed(0)}% ·{" "}
          {state.automation.min_humidity.toFixed(0)}–
          {state.automation.max_humidity.toFixed(0)}%
        </p>
      </article>
    </div>
  );
}
