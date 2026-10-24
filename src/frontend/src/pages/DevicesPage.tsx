/**
 * Devices page: one editor per logical device.
 *
 * Free channels are selected from the list returned by the server: do not invent relay numbering, the interface does not handle it, the number of channels is known by the hardware.

 */

import { useCallback, useEffect, useState } from "react";

import { Card } from "../components/Card";
import { DeviceEditor } from "../features/devices/DeviceEditor";
import { useRealtime } from "../services/realtime";
import { needsReload } from "../features/home/reducer";
import * as api from "../services/api";
import type { Capability, Device, DeviceKind } from "../services/types";

/** Number of relay channels per board: a board cannot handle more than six devices. */
const CHANNELS = [1, 2, 3, 4, 5, 6];

export function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDevices(await api.fetchDevices());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to load devices");
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
   * Creates a device on the first free channel.
   *
   * @returns Nothing: the list is reloaded after the server response.
   */
  async function create(): Promise<void> {
    const free = CHANNELS.find((channel) => !taken.includes(channel));
    if (free === undefined) {
      setError("No free channels left");
      return;
    }
    try {
      await api.createDevice({
        name: `Device ${free}`,
        kind: "OTHER" as DeviceKind,
        channel: free,
        capabilities: ["ON", "OFF"] as Capability[],
        automation_enabled: false,
      });
      await load();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to create device");
    }
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Devices</h1>
          <p className="page__subtitle">Logical devices over relay channels</p>
        </div>
        <button className="button button--primary" type="button" onClick={() => void create()}>
          Add device
        </button>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <Card title="Configuration" hint="Name, type, channel and capabilities">
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
