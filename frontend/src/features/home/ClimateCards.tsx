/** Climate cards with the current temperature and humidity. */

import type { HomeState } from "../../services/types";

interface ClimateProps {
  state: HomeState;
}

export function Climate({ state }: ClimateProps) {
  const temperature = state.temperature;
  const humidity = state.humidity;

  return (
    <div className="grid grid--climate">
      <article className="metric-card">
        <span className="metric-card__ring" />
        <div className="metric-card__label">Температура</div>
        <p className="metric">
          {temperature === null ? "—" : temperature.toFixed(1)}
          {temperature !== null ? <span className="metric__unit">°C</span> : null}
        </p>
        <p className="metric__note">
          цель {state.automation.target_temperature.toFixed(1)}°C ·{" "}
          {state.automation.min_temperature.toFixed(1)}–
          {state.automation.max_temperature.toFixed(1)}°C
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
