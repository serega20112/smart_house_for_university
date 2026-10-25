import "./automation-form.css";
/**
 * Настройка автоматизации: цели, допуски и участники.
 *
 * Экран показывает ровно то, чем командует бэкенд: две цели с коридорами вокруг них и
 * список устройств, которые автоматика вправе трогать. Пороги срабатывания, очереди и
 * «приоритеты» выдумывать негде — их в прикладном слое нет.
 *
 * Значения приезжают в цельсиях и в них же сохраняются: перевод в фаренгейты живёт
 * только на показе, иначе округление дважды исказило бы цель. Допуск — это разница, а не
 * точка, поэтому он умножается на 1.8, но не смещается на 32.
 */

import { useState, type FormEvent } from "react";

import * as api from "@/shared/api/client";
import { notify } from "@/shared/lib/notify";
import { RangeBar, Toggle } from "@/shared/ui";
import type { Automation, Device, Reading, TemperatureUnit } from "@/shared/api/types";

/** Границы, которые примет сервер: те же, что в `requests/automation.py`. */
const TEMPERATURE_MIN = -50;
const TEMPERATURE_MAX = 80;
const TEMPERATURE_TOLERANCE_MAX = 20;
const HUMIDITY_TOLERANCE_MAX = 50;

/** Сколько знаков после запятой у температуры на этом экране. */
const TEMPERATURE_STEP = 1;

/**
 * Возвращает температуру в единице, которую выбрал аккаунт.
 *
 * @param celsius Значение в цельсиях.
 * @param unit Единица показа.
 * @returns Число для поля и для линейки.
 */
function toShown(celsius: number, unit: TemperatureUnit): number {
  return unit === "C" ? celsius : celsius * 1.8 + 32;
}

/**
 * Возвращает цельсию из числа, которое человек видит в своей единице.
 *
 * @param value Число в единице показа.
 * @param unit Единица показа.
 * @returns Значение в цельсиях, как его хранит сервер.
 */
function toStored(value: number, unit: TemperatureUnit): number {
  return unit === "C" ? value : (value - 32) / 1.8;
}

/**
 * Возвращает допуск в единице показа: разница переводится без смещения.
 *
 * @param celsius Допуск в цельсиях.
 * @param unit Единица показа.
 * @returns Тот же интервал в выбранной единице.
 */
function toShownDelta(celsius: number, unit: TemperatureUnit): number {
  return unit === "C" ? celsius : celsius * 1.8;
}

interface BandProps {
  label: string;
  value: number | null;
  target: number;
  tolerance: number;
  suffix: string;
  decimals: number;
  min: number;
  max: number;
  toleranceMax: number;
  onValue: (next: number) => void;
  onTolerance: (next: number) => void;
}

/**
 * Рисует блок «цель + допуск»: линейку сверху и два поля ниже.
 *
 * @param props.label Что настраиваем.
 * @param props.value Измеренное значение или None, пока датчик молчит.
 * @param props.target Цель в единице показа.
 * @param props.tolerance Допуск в единице показа.
 * @param props.suffix Единица, дописываемая к числу.
 * @param props.decimals Сколько знаков после запятой показывать.
 * @param props.min Наименьшее значение цели, которое примет сервер.
 * @param props.max Наибольшее значение цели.
 * @param props.toleranceMax Наибольший допуск.
 * @param props.onValue Куда передать новое значение цели.
 * @param props.onTolerance Куда передать новый допуск.
 * @returns Разметка блока.
 */
function Band({
  label,
  value,
  target,
  tolerance,
  suffix,
  decimals,
  min,
  max,
  toleranceMax,
  onValue,
  onTolerance,
}: BandProps) {
  const format = (item: number): string => `${item.toFixed(decimals)}${suffix}`;

  return (
    <div className="band">
      <div className="band__head">
        <span className="band__label">{label}</span>
        <span className="band__value num">
          {format(target - tolerance)} … {format(target + tolerance)}
        </span>
      </div>

      <RangeBar value={value} target={target} tolerance={tolerance} format={format} />

      <div className="band__fields">
        <label className="field">
          <span className="field__label">Цель</span>
          <input
            className="field__input"
            type="number"
            step={decimals === 0 ? 1 : 0.1}
            min={min}
            max={max}
            value={target}
            onChange={(event) => onValue(Number(event.target.value))}
          />
        </label>
        <label className="field">
          <span className="field__label">Допуск</span>
          <input
            className="field__input"
            type="number"
            step={decimals === 0 ? 1 : 0.1}
            min={0}
            max={toleranceMax}
            value={tolerance}
            onChange={(event) => onTolerance(Number(event.target.value))}
          />
        </label>
      </div>
    </div>
  );
}

interface AutomationFormProps {
  automation: Automation;
  reading: Reading;
  devices: Device[];
  unit: TemperatureUnit;
  onSaved: () => void;
}

/**
 * Возвращает форму настройки автоматизации.
 *
 * @param props.automation Настройка, пришедшая с сервера.
 * @param props.reading Живые значения климата: по ним линейка показывает точку.
 * @param props.devices Устройства аккаунта: из них выбирают участников.
 * @param props.unit Единица, в которой человек видит температуру.
 * @param props.onSaved Вызывается, когда сервер принял настройку.
 */
export function AutomationForm({
  automation,
  reading,
  devices,
  unit,
  onSaved,
}: AutomationFormProps) {
  const [enabled, setEnabled] = useState(automation.enabled);
  const [temperature, setTemperature] = useState(toShown(automation.target_temperature, unit));
  const [temperatureTolerance, setTemperatureTolerance] = useState(
    toShownDelta(automation.temperature_tolerance, unit),
  );
  const [humidity, setHumidity] = useState(automation.target_humidity);
  const [humidityTolerance, setHumidityTolerance] = useState(automation.humidity_tolerance);
  const [participants, setParticipants] = useState<string[]>(automation.participating_device_ids);
  const [busy, setBusy] = useState(false);

  /**
   * Ставит или снимает устройство из участников автоматики.
   *
   * @param deviceId Идентификатор устройства.
   */
  function toggleParticipant(deviceId: string): void {
    setParticipants((current) =>
      current.includes(deviceId)
        ? current.filter((item) => item !== deviceId)
        : [...current, deviceId],
    );
  }

  /**
   * Отправляет настройку: сервер принимает её одной заменой.
   *
   * @param event Событие отправки формы.
   */
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    try {
      await api.updateAutomation({
        enabled,
        target_temperature: Number(toStored(temperature, unit).toFixed(2)),
        temperature_tolerance: Number(
          (unit === "C" ? temperatureTolerance : temperatureTolerance / 1.8).toFixed(2),
        ),
        target_humidity: humidity,
        humidity_tolerance: humidityTolerance,
        participating_device_ids: participants,
      });
      notify("Автоматизация сохранена", "ok");
      onSaved();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Настройка не сохранилась", "bad");
    } finally {
      setBusy(false);
    }
  }

  // Исключённое из управления устройство автоматика не трогает, поэтому его и не предлагаем.
  const suitable = devices.filter((device) => device.enabled);

  return (
    <form className="aform" onSubmit={(event) => void submit(event)}>
      <div className="aform__mode">
        <div className="switch-row">
          <span className="switch-row__text">
            <span className="switch-row__title">Автоматика включена</span>
            <span className="switch-row__note">
              Пока выключено, цели держат только сценарии и руки
            </span>
          </span>
        </div>
        <Toggle checked={enabled} disabled={busy} label="Автоматика включена" onChange={setEnabled} />
      </div>

      <div className="aform__ranges">
        <Band
          label="Температура"
          value={reading.temperature === null ? null : toShown(reading.temperature, unit)}
          target={Number(temperature.toFixed(TEMPERATURE_STEP))}
          tolerance={Number(temperatureTolerance.toFixed(TEMPERATURE_STEP))}
          suffix={unit === "C" ? "°C" : "°F"}
          decimals={TEMPERATURE_STEP}
          min={toShown(TEMPERATURE_MIN, unit)}
          max={toShown(TEMPERATURE_MAX, unit)}
          toleranceMax={toShownDelta(TEMPERATURE_TOLERANCE_MAX, unit)}
          onValue={setTemperature}
          onTolerance={setTemperatureTolerance}
        />
        <Band
          label="Влажность"
          value={reading.humidity}
          target={humidity}
          tolerance={humidityTolerance}
          suffix="%"
          decimals={0}
          min={0}
          max={100}
          toleranceMax={HUMIDITY_TOLERANCE_MAX}
          onValue={setHumidity}
          onTolerance={setHumidityTolerance}
        />
      </div>

      <div className="field">
        <span className="field__label">Устройства в автоматике</span>
        {suitable.length === 0 ? (
          <p className="empty">
            <span className="empty__title">Нет разрешённых устройств</span>
            Разрешите управление хотя бы одному устройству в разделе «Устройства».
          </p>
        ) : (
          <div className="chips">
            {suitable.map((device) => (
              <button
                key={device.id}
                type="button"
                aria-pressed={participants.includes(device.id)}
                className={`chip ${participants.includes(device.id) ? "chip--active" : ""}`.trim()}
                onClick={() => toggleParticipant(device.id)}
              >
                {device.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <footer className="aform__foot">
        <p className="aform__note">
          Ручная команда ставит автоматику на паузу и возвращается сама. Участие устройства
          в списке ещё не значит, что оно подходит под цель: способность проверяется на
          сервере.
        </p>
        <button className="button button--primary" type="submit" disabled={busy}>
          {busy ? "Сохраняю…" : "Сохранить настройку"}
        </button>
      </footer>
    </form>
  );
}
