/**
 * Готовые компоненты, из которых собирается главный экран.
 *
 * Каждый виджет — компонент, который о конкретном доме не знает ничего. Какие
 * компоненты появятся, в каком порядке и под каким личным заголовком, приходит с
 * сервера, поэтому одна и та же сборка рисует свою проекцию приложения каждому
 * аккаунту.
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
 * Рисует сохранённый список виджетов готовыми компонентами.
 *
 * Виджет, указывающий на исчезнувшее устройство, пропускается, а не ломает экран:
 * раскладку, поправленную в другой вкладке, человек не должен видеть половину.
 *
 * @param props.widgets Порядок виджетов, пришедший с сервера.
 * @param props.state Живой снимок текущего аккаунта.
 * @param props.preferences Сохранённые настройки интерфейса.
 * @param props.loading Идёт ли ещё первая загрузка снимка.
 * @param props.onError Вызывается с человеческим текстом отказа.
 * @param props.onChanged Вызывается после того, как команда что-то изменила.
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
