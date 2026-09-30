/** Devices page: one editor per logical device. */

import { useCallback, useEffect, useState } from "react";

import { Card } from "../components/Card";
import { DeviceEditor } from "../features/devices/DeviceEditor";
import { useRealtime } from "../services/realtime";
import { needsReload } from "../features/home/reducer";
import * as api from "../services/api";
import type { Capability, Device, DeviceType } from "../services/types";

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
    onMessage: (message) => {
      if (needsReload(message.type)) {
        void load();
      }
    },
  });

  const taken = devices.map((device) => device.physical_channel);

  async function create(): Promise<void> {
    const free = [1, 2, 3, 4, 5, 6].find((channel) => !taken.includes(channel));
    if (free === undefined) {
      setError("Свободных каналов не осталось");
      return;
    }
    try {
      await api.createDevice({
        name: `Устройство ${free}`,
        type: "OTHER" as DeviceType,
        physical_channel: free,
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
