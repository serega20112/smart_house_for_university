/** Automation settings form. */

import { useState } from "react";

import { Card } from "../../components/Card";
import { Toggle } from "../../components/Toggle";
import * as api from "../../services/api";
import type { Automation, Device } from "../../services/types";

interface AutomationFormProps {
  automation: Automation;
  devices: Device[];
  onSaved: (message: string) => void;
  onError: (message: string) => void;
}

export function AutomationForm({
  automation,
  devices,
  onSaved,
  onError,
}: AutomationFormProps) {
  const [enabled, setEnabled] = useState(automation.enabled);
  const [targetTemperature, setTargetTemperature] = useState(
    automation.target_temperature,
  );
  const [temperatureTolerance, setTemperatureTolerance] = useState(
    automation.target_temperature - automation.min_temperature,
  );
  const [targetHumidity, setTargetHumidity] = useState(automation.target_humidity);
  const [humidityTolerance, setHumidityTolerance] = useState(
    automation.target_humidity - automation.min_humidity,
  );
  const [participants, setParticipants] = useState<number[]>(automation.participating_device_ids);
  const [busy, setBusy] = useState(false);

  const effective = participants.length > 0 ? participants : devices.map((d) => d.id);

  function toggleParticipant(deviceId: number): void {
    setParticipants((current) =>
      current.includes(deviceId)
        ? current.filter((item) => item !== deviceId)
        : [...current, deviceId],
    );
  }

  async function run(action: () => Promise<{ message: string }>, done: () => void): Promise<void> {
    setBusy(true);
    try {
      const result = await action();
      onSaved(result.message);
      done();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Не удалось сохранить настройки");
    } finally {
      setBusy(false);
    }
  }

  function save(): Promise<void> {
    return run(
      () =>
        api.updateAutomation({
          target_temperature: targetTemperature,
          temperature_tolerance: temperatureTolerance,
          target_humidity: targetHumidity,
          humidity_tolerance: humidityTolerance,
          participating_device_ids: effective,
        }),
      () => undefined,
    );
  }

  function toggleAuto(next: boolean): Promise<void> {
    return run(
      () => api.setAutomationEnabled(next),
      () => setEnabled(next),
    );
  }

  return (
    <Card title="Автоматизация" hint="Гистерезис не даёт устройствам метаться">
      <div className="form">
        <div className="form__row">
          <div>
            <p className="form__label">Автоматический режим</p>
            <p className="form__note">
              {enabled ? "Устройства сами держат климат" : "Устройства только вручную"}
            </p>
          </div>
          <Toggle
            checked={enabled}
            disabled={busy}
            label="Автоматизация"
            onChange={(next) => void toggleAuto(next)}
          />
        </div>

        <div className="range">
          <div className="range__head">
            <span>Температура</span>
            <strong>
              {(targetTemperature - temperatureTolerance).toFixed(1)} –{" "}
              {(targetTemperature + temperatureTolerance).toFixed(1)}°C
            </strong>
          </div>
          <label className="field">
            <span>Цель, °C</span>
            <input
              type="number"
              step="0.5"
              value={targetTemperature}
              onChange={(event) => setTargetTemperature(Number(event.target.value))}
            />
          </label>
          <label className="field">
            <span>Допуск, °C</span>
            <input
              type="number"
              step="0.5"
              min="0"
              value={temperatureTolerance}
              onChange={(event) => setTemperatureTolerance(Number(event.target.value))}
            />
          </label>
        </div>

        <div className="range">
          <div className="range__head">
            <span>Влажность</span>
            <strong>
              {(targetHumidity - humidityTolerance).toFixed(0)} –{" "}
              {(targetHumidity + humidityTolerance).toFixed(0)}%
            </strong>
          </div>
          <label className="field">
            <span>Цель, %</span>
            <input
              type="number"
              step="1"
              value={targetHumidity}
              onChange={(event) => setTargetHumidity(Number(event.target.value))}
            />
          </label>
          <label className="field">
            <span>Допуск, %</span>
            <input
              type="number"
              step="1"
              min="0"
              value={humidityTolerance}
              onChange={(event) => setHumidityTolerance(Number(event.target.value))}
            />
          </label>
        </div>

        <div className="field">
          <span>Устройства автоматизации</span>
          <div className="chips">
            {devices.map((device) => {
              const active = effective.includes(device.id);
              return (
                <button
                  key={device.id}
                  type="button"
                  aria-pressed={active}
                  className={`chip ${active ? "chip--active" : ""}`.trim()}
                  onClick={() => toggleParticipant(device.id)}
                >
                  {device.name}
                </button>
              );
            })}
          </div>
        </div>

        <button
          className="button button--primary"
          type="button"
          disabled={busy}
          onClick={() => void save()}
        >
          Сохранить
        </button>
      </div>
    </Card>
  );
}
