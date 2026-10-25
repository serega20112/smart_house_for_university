import "./scenario-composer.css";
/**
 * Постановка отложенного действия.
 *
 * Сценарий — обещание, которое дом даёт сам себе: одно действие, срок начала, иногда
 * граница длительности и поведение после. Форма рисует ровно эти четыре вещи и ничего
 * больше: списков устройств и «цепочек» прикладной слой не знает.
 *
 * Экран пересчитывает момент начала из задержки, чтобы человек видел календарь, а не
 * абстрактные минуты.
 */

import { useMemo, useState, type FormEvent } from "react";

import * as api from "@/shared/api/client";
import { formatClock, formatMoment } from "@/shared/lib/format";
import { notify } from "@/shared/lib/notify";
import {
  CAPABILITY_LABELS,
  COMPLETION_LABELS,
  SCENARIO_CAPABILITY_ORDER,
} from "@/shared/lib/labels";
import type { Capability, CompletionBehavior } from "@/shared/api/types";

/** Серверные границы задержки и длительности: больше — не примет. */
const DELAY_MAX_MINUTES = 10080;
const DURATION_MAX_MINUTES = 10080;
const TARGET_MAX_LENGTH = 120;

/** Способности, которым нужна температура цели. */
const TEMPERATURE_CAPABILITIES: readonly Capability[] = ["HEAT", "COOL"];

interface ScenarioComposerProps {
  onScheduled: () => void;
}

/**
 * Возвращает форму одного отложенного действия.
 *
 * @param props.onScheduled Вызывается, когда сценарий ушёл в расписание.
 */
export function ScenarioComposer({ onScheduled }: ScenarioComposerProps) {
  const [capability, setCapability] = useState<Capability>("ON");
  const [delay, setDelay] = useState(0);
  const [duration, setDuration] = useState<number | null>(null);
  const [target, setTarget] = useState("");
  const [temperature, setTemperature] = useState(22);
  const [behavior, setBehavior] = useState<CompletionBehavior>("LEAVE_TO_AUTOMATION");
  const [busy, setBusy] = useState(false);

  const needsTemperature = TEMPERATURE_CAPABILITIES.includes(capability);

  // Момент начала считается из задержки: показывать абстрактные минуты неудобно.
  const startAt = useMemo(() => new Date(Date.now() + delay * 60_000), [delay]);

  /**
   * Отправляет сценарий в расписание дома.
   *
   * @param event Событие отправки формы.
   */
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    try {
      await api.scheduleScenario({
        capability,
        delay_minutes: delay,
        duration_minutes: duration,
        target: target.trim() || null,
        target_temperature: needsTemperature ? temperature : null,
        completion_behavior: behavior,
      });
      notify(
        `${CAPABILITY_LABELS[capability]} · начало в ${formatClock(startAt.toISOString())}`,
        "ok",
      );
      onScheduled();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Сценарий не поставлен", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="composer" onSubmit={(event) => void submit(event)}>
      <header className="composer__head">
        <h2 className="composer__title">Отложить действие</h2>
        <p className="composer__note">
          Начало {formatMoment(startAt.toISOString())}
          {duration === null ? "" : ` · идёт не дольше ${duration} мин`}
        </p>
      </header>

      <div className="composer__grid">
        <label className="field">
          <span className="field__label">Что сделать</span>
          <select
            value={capability}
            onChange={(event) => setCapability(event.target.value as Capability)}
          >
            {SCENARIO_CAPABILITY_ORDER.map((item) => (
              <option key={item} value={item}>
                {CAPABILITY_LABELS[item]}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Через, минут</span>
          <input
            className="field__input"
            type="number"
            min={0}
            max={DELAY_MAX_MINUTES}
            step={5}
            value={delay}
            onChange={(event) => setDelay(Number(event.target.value))}
          />
        </label>

        <label className="field">
          <span className="field__label">Длительность, минут</span>
          <input
            className="field__input"
            type="number"
            min={1}
            max={DURATION_MAX_MINUTES}
            step={5}
            value={duration ?? ""}
            placeholder="Без границы"
            onChange={(event) =>
              setDuration(event.target.value === "" ? null : Number(event.target.value))
            }
          />
        </label>

        {needsTemperature ? (
          <label className="field">
            <span className="field__label">Цель, °C</span>
            <input
              className="field__input"
              type="number"
              min={-50}
              max={80}
              step={0.5}
              value={temperature}
              onChange={(event) => setTemperature(Number(event.target.value))}
            />
          </label>
        ) : null}

        <label className="field">
          <span className="field__label">Что после</span>
          <select
            value={behavior}
            onChange={(event) => setBehavior(event.target.value as CompletionBehavior)}
          >
            {(Object.keys(COMPLETION_LABELS) as CompletionBehavior[]).map((item) => (
              <option key={item} value={item}>
                {COMPLETION_LABELS[item]}
              </option>
            ))}
          </select>
        </label>

        <label className="field composer__wide">
          <span className="field__label">Место или предмет</span>
          <input
            className="field__input"
            value={target}
            maxLength={TARGET_MAX_LENGTH}
            placeholder="Комната, гирлянда, аквариум — как вы это назвали"
            onChange={(event) => setTarget(event.target.value)}
          />
        </label>
      </div>

      <footer className="composer__foot">
        <p className="composer__hint">
          Пока сценарий идёт, автоматика держит паузу — так устроено приложение.
        </p>
        <button className="button button--primary" type="submit" disabled={busy}>
          {busy ? "Ставлю…" : "Поставить в расписание"}
        </button>
      </footer>
    </form>
  );
}
