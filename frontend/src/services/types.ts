/** Shapes returned by the backend REST API. */

export type DeviceStatus = "ON" | "OFF" | "COOL" | "HEAT" | "UNAVAILABLE";

export type Capability = "ON" | "OFF" | "COOL" | "HEAT";

export type DeviceType =
  | "LIGHT"
  | "FAN"
  | "HUMIDIFIER"
  | "AIR_CONDITIONER"
  | "HEATER"
  | "OUTLET"
  | "OTHER";

export interface Device {
  id: number;
  name: string;
  type: DeviceType;
  physical_channel: number;
  capabilities: Capability[];
  enabled: boolean;
  automation_enabled: boolean;
  status: DeviceStatus;
}

export interface Automation {
  enabled: boolean;
  target_temperature: number;
  min_temperature: number;
  max_temperature: number;
  target_humidity: number;
  min_humidity: number;
  max_humidity: number;
  participating_device_ids: number[];
}

export interface Scenario {
  id: number;
  status: string;
  created_at: string;
  start_at: string;
  duration_minutes: number | null;
  target: string | null;
  actions: { capability: string; target_value: number | null }[];
  completion_behavior: string;
}

export interface HomeState {
  backend_online: boolean;
  esp_online: boolean;
  manual_override: boolean;
  temperature: number | null;
  humidity: number | null;
  devices: Device[];
  automation: Automation;
  active_scenarios: Scenario[];
}

export interface ExecutionResult {
  status: string;
  message: string;
  device: { id: number; name: string; physical_channel: number } | null;
  capability: string | null;
}

export interface CommandResult {
  status: string;
  intent: string | null;
  confidence: number;
  message: string;
  requires_clarification: boolean;
  clarification: string | null;
  scenario_id: number | null;
}

export interface SettingsResult {
  status: string;
  message: string;
  automation: Automation;
}

export type RealtimeEvent =
  | "device.state_changed"
  | "sensor.temperature_changed"
  | "sensor.humidity_changed"
  | "esp.connected"
  | "esp.disconnected"
  | "esp.error"
  | "automation.state_changed"
  | "scenario.created"
  | "scenario.started"
  | "scenario.completed"
  | "scenario.failed"
  | "devices.updated";
