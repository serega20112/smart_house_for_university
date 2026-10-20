/**
 * Generic components the dashboard is built from.
 *
 * Every widget type is a component that knows nothing about a particular home.
 * Which components appear, in which order and under which personal title comes
 * from the server, so the same bundle renders a different projection of the
 * application for every signed in account.
 */

import { Card } from "../../components/Card";
import type { HomeState, Preferences, Widget } from "../../services/types";
import { Climate } from "./ClimateCards";
import { CommandChat } from "./CommandChat";
import { DeviceCard } from "./DeviceCard";

export interface DashboardProps {
  widgets: Widget[];
  state: HomeState;
  preferences: Preferences | null;
  loading: boolean;
  onError: (message: string) => void;
  onChanged: () => void;
}

/**
 * Renders the stored widget list with the generic components.
 *
 * A widget pointing at a device that no longer exists is skipped instead of
 * breaking the screen, so a layout edited on another tab can never leave the
 * dashboard half rendered.
 *
 * @param props.widgets Ordered layout coming from the server.
 * @param props.state Live snapshot of the current account.
 * @param props.preferences Stored interface preferences.
 * @param props.loading Whether the snapshot is still loading.
 * @param props.onError Called with a human readable failure.
 * @param props.onChanged Called after a command changed something.
 */
export function Dashboard({
  widgets,
  state,
  preferences,
  loading,
  onError,
  onChanged,
}: DashboardProps) {
  const devices = new Map(state.devices.map((device) => [device.id, device]));
  const unit = preferences?.temperature_unit ?? "C";
  const layout = widgets.length > 0 ? widgets : DEFAULT_WIDGETS;

  return (
    <div className="grid grid--dashboard">
      {layout.map((widget, index) => {
        const key = `${widget.type}-${widget.device_id ?? "global"}-${index}`;
        if (widget.type === "climate" || widget.type === "sensor") {
          return (
            <section key={key} data-widget={widget.type}>
              <Card title={widget.title ?? "Климат"} hint="Датчики платы">
                <Climate state={state} unit={unit} />
              </Card>
            </section>
          );
        }
        if (widget.type === "command") {
          if (preferences?.show_command_chat === false) {
            return null;
          }
          return (
            <section key={key} data-widget="command">
              <CommandChat title={widget.title ?? "Команды"} />
            </section>
          );
        }
        const device = widget.device_id === null ? undefined : devices.get(widget.device_id);
        if (!device) {
          return null;
        }
        return (
          <section key={key} data-widget="device">
            <DeviceCard
              device={device}
              title={widget.title ?? undefined}
              onError={onError}
              onChanged={onChanged}
            />
          </section>
        );
      })}
      {loading ? <p className="empty">Загружаю состояние…</p> : null}
    </div>
  );
}

const DEFAULT_WIDGETS: Widget[] = [
  { type: "climate", device_id: null, title: "Климат" },
  { type: "command", device_id: null, title: "Команды" },
];
