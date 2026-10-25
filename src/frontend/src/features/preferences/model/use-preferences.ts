/**
 * Настройки проекции дома.
 *
 * Единицы, тема и панель команд принадлежат аккаунту, а не браузеру: человек должен
 * увидеть свой дом так же с любого компьютера. Поэтому каждое изменение сначала уезжает
 * на сервер, а уже потом считается удавшимся.
 *
 * Тема — единственное исключение: она применяется мгновенно и локально, иначе экран ждал
 * бы ответа сети, а отказ сервера видно по уведомлению.
 */

import { useCallback, useState } from "react";

import { useSession } from "@/entities/session";
import * as api from "@/shared/api/client";
import { notify } from "@/shared/lib/notify";
import { applyTheme, rememberTheme, type ThemeName } from "@/shared/lib/theme";
import type { Preferences, TemperatureUnit } from "@/shared/api/types";

/** Чем хук делится с тем, кто рисует настройки. */
export interface PreferencesStore {
  preferences: Preferences | null;
  unit: TemperatureUnit;
  theme: ThemeName;
  showCommandChat: boolean;
  busy: boolean;
  changeUnit: (next: TemperatureUnit) => Promise<void>;
  changeTheme: (next: ThemeName) => void;
  toggleCommandChat: (next: boolean) => Promise<void>;
}

/**
 * Возвращает настройки аккаунта и способы их менять.
 *
 * @returns Значения настроек, признак занятого места и три действия.
 */
export function usePreferences(): PreferencesStore {
  const { preferences, refreshPreferences } = useSession();
  const [busy, setBusy] = useState(false);

  /**
   * Применяет частичное изменение и сообщает, чем оно кончилось.
   *
   * @param changes Поля, которые человек поменял.
   * @param done Текст подтверждения, когда сервер запись принял.
   */
  const patch = useCallback(
    async (changes: Partial<Preferences>, done: string): Promise<void> => {
      setBusy(true);
      try {
        await api.updatePreferences(changes);
        await refreshPreferences();
        notify(done, "ok");
      } catch (exc) {
        notify(exc instanceof Error ? exc.message : "Настройка не сохранилась", "bad");
        // Значение на экране обязано вернуться к тому, что сервер действительно держит.
        await refreshPreferences();
      } finally {
        setBusy(false);
      }
    },
    [refreshPreferences],
  );

  const changeUnit = useCallback(
    (next: TemperatureUnit) => patch({ temperature_unit: next }, `Температура в ${next === "C" ? "°C" : "°F"}`),
    [patch],
  );

  const toggleCommandChat = useCallback(
    (next: boolean) => patch({ show_command_chat: next }, next ? "Панель команд показана" : "Панель команд скрыта"),
    [patch],
  );

  const changeTheme = useCallback(
    (next: ThemeName) => {
      applyTheme(next);
      rememberTheme(next);
      void patch({ theme: next }, next === "light" ? "Светлая тема" : "Тёмная тема");
    },
    [patch],
  );

  return {
    preferences,
    unit: preferences?.temperature_unit ?? "C",
    theme: preferences?.theme ?? "dark",
    showCommandChat: preferences?.show_command_chat ?? true,
    busy,
    changeUnit,
    changeTheme,
    toggleCommandChat,
  };
}
