/** Grid of the six device cards. */

import { Card } from "../../components/Card";
import type { Device } from "../../services/types";
import { DeviceCard } from "./DeviceCard";

interface DeviceGridProps {
  devices: Device[];
  onError: (message: string) => void;
  onChanged: () => void;
}

export function DeviceGrid({ devices, onError, onChanged }: DeviceGridProps) {
  return (
    <Card title="Устройства" hint="Шесть релейных каналов">
      <div className="grid grid--devices">
        {devices.map((device) => (
          <DeviceCard
            key={device.id}
            device={device}
            onError={onError}
            onChanged={onChanged}
          />
        ))}
      </div>
    </Card>
  );
}
