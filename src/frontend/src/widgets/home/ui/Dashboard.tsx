import "./dashboard.css";
/**
 * Главный экран дома, собранный из сохранённой раскладки.
 *
 * Каждый блок — компонент, который о конкретном доме не знает ничего: какие карточки
 * показать, в каком порядке и под каким личным заголовком приходит с сервера. Поэтому
 * одна и та же сборка рисует свою проекцию каждому аккаунту.
 *
 * Раскладка бенто: слева климат над устройствами, справа во всю высоту — панель команд.
 * Когда команд нет, колонки схлопываются в одну, и экран не остаётся с пустой дырой.
 */

import { Skeleton } from "@/shared/ui";
import { isDeviceActive } from "@/shared/lib/labels";
import type { Board, Device, HomeState, Preferences, Widget } from "@/shared/api/types";
import { Climate } from "./Climate";
import { CommandChat } from "./CommandChat";
import { DeviceCard } from "./DeviceCard";

/** Виджет устройства вместе с самим устройством из снимка. */
interface DeviceEntry {
  widget: Widget;
  device: Device;
}

export interface DashboardProps {
  widgets: Widget[];
  state: HomeState | null;
  preferences: Preferences | null;
  boards: Board[];
  loading: boolean;
  onChanged: () => void;
}

/**
 * Рисует сохранённый список виджетов готовыми компонентами.
 *
 * Виджет, указывающий на исчезнувшее устройство, пропускается, а не ломает экран:
 * раскладку, поправленную в другой вкладке, человек не должен видеть наполовину.
 *
 * @param props.widgets Порядок виджетов, пришедший с сервера.
 * @param props.state Живой снимок текущего аккаунта или None до первого чтения.
 * @param props.preferences Настройки интерфейса: единицы и видимость панели команд.
 * @param props.boards Платы аккаунта: по ним плитка показывает, где стоит канал.
 * @param props.loading Идёт ли ещё первая загрузка.
 * @param props.onChanged Вызывается после того, как команда что-то изменила.
 */
export function Dashboard({ widgets, state, preferences, boards, loading, onChanged }: DashboardProps) {
  const unit = preferences?.temperature_unit ?? "C";
  const layout = widgets.length > 0 ? widgets : DEFAULT_WIDGETS;
  const showChat = preferences?.show_command_chat !== false;

  const climateWidgets = layout.filter(
    (widget) => widget.type === "climate" || widget.type === "sensor",
  );
  const commandWidget = showChat ? layout.find((widget) => widget.type === "command") : undefined;

  const devices = new Map((state?.devices ?? []).map((device) => [device.id, device]));
  const names = new Map(boards.map((board) => [board.id, board.name]));

  // Виджет без устройства — это уже удалённое устройство: его просто не показываем.
  const deviceCards: DeviceEntry[] = layout
    .filter((widget) => widget.type === "device")
    .map((widget) => ({
      widget,
      device: widget.device_id === null ? undefined : devices.get(widget.device_id),
    }))
    .filter((entry): entry is DeviceEntry => entry.device !== undefined);

  const on = deviceCards.filter((entry) => isDeviceActive(entry.device.status)).length;

  if (loading && state === null) {
    return (
      <div className="home home--loading">
        <Skeleton variant="climate" />
        <Skeleton variant="tiles" />
      </div>
    );
  }

  if (state === null) {
    return <p className="notice notice--bad">Состояние дома не прочиталось.</p>;
  }

  return (
    <div className={`home ${commandWidget ? "home--split" : "home--wide"}`}>
      <div className="home__main">
        {climateWidgets.length > 0 ? (
          <Climate
            state={state}
            unit={unit}
            title={climateWidgets[0].title ?? "Климат"}
          />
        ) : null}

        {deviceCards.length > 0 ? (
          <section className="home__devices">
            <header className="home__zone-head">
              <h2 className="home__zone-title">Устройства</h2>
              <p className="home__zone-note">
                {on} из {deviceCards.length} включено
              </p>
            </header>

            <div className="grid grid--devices">
              {deviceCards.map(({ widget, device }) => (
                <DeviceCard
                  key={device.id}
                  device={device}
                  title={widget.title ?? undefined}
                  boardName={device.board_id ? names.get(device.board_id) : undefined}
                  onChanged={onChanged}
                />
              ))}
            </div>
          </section>
        ) : (
          <div className="empty">
            <p className="empty__title">На главном экране нет плиток</p>
            <p>Заведите устройство на экране «Устройства» — плитка появится здесь сама.</p>
          </div>
        )}
      </div>

      {commandWidget ? (
        <aside className="home__command">
          <CommandChat title={commandWidget.title ?? "Команды"} onChanged={onChanged} />
        </aside>
      ) : null}
    </div>
  );
}

/** Раскладка по умолчанию: климат и панель команд, пока аккаунт ничего не собрал. */
const DEFAULT_WIDGETS: Widget[] = [
  { type: "climate", device_id: null, title: "Климат" },
  { type: "command", device_id: null, title: "Команды" },
];
