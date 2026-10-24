/**
 * Страница устройств: по редактору на каждое логическое устройство.
 *
 * Свободный канал здесь выбирают по списку, который вернул сервер: придумывать
 * нумерацию реле интерфейс не берётся, их число знает железо.
 */

import { useCallback, useEffect, useState } from "react";

import { Card } from "../components/Card";
import { DeviceEditor } from "../features/devices/DeviceEditor";
import { useRealtime } from "../services/realtime";
import { needsReload } from "../features/home/reducer";
import * as api from "../services/api";
import type { Capability, Device, DeviceKind } from "../services/types";

/** Число каналов реле одной платы: больше шести устройств плата не потянет. */
const CHANNELS = [1, 2, 3, 4, 5, 6];

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDevices(await api.fetchDevices());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось загрузить устройства");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useRealtime({
    enabled: true,
    onMessage: (message) => {
      if (needsReload(message.type)) {
        void load();
      }
    },
  });

  const taken = devices.map((device) => device.channel);

  /**
   * Заводит устройство на первом свободном канале.
   *
   * @returns Ничего: список перечитывается после ответа сервера.
   */
  async function create(): Promise<void> {
    const free = CHANNELS.find((channel) => !taken.includes(channel));
    if (free === undefined) {
      setError("Свободных каналов не осталось");
      return;
    }
    try {
      await api.createDevice({
        name: `Устройство ${free}`,
        kind: "OTHER" as DeviceKind,
        channel: free,
        capabilities: ["ON", "OFF"] as Capability[],
        automation_enabled: false,
      });
      await load();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось создать устройство");
    }
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Устройства</h1>
          <p className="page__subtitle">Логические устройства поверх релейных каналов</p>
        </div>
        <button className="button button--primary" type="button" onClick={() => void create()}>
          Добавить устройство
        </button>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <Card title="Конфигурация" hint="Название, тип, канал и возможности">
        <div className="grid grid--editors">
          {devices.map((device) => (
            <DeviceEditor
              key={device.id}
              device={device}
              takenChannels={taken}
              onSaved={() => void load()}
              onError={setError}
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
