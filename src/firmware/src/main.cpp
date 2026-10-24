// ============================================================================
// Умный дом — прошивка ESP8266
//
// Плата — исполнительный орган и источник показаний: она входит в Wi-Fi, водит
// шестью каналами реле, читает DHT22, выполняет команды сервера и докладывает о
// своём состоянии. Автоматика, сценарии, хранение, понимание фраз и вся логика
// живут на сервере — плата никогда не выбирает устройство сама.
//
// ГЛАВНЫЙ ФАЙЛ ЗДЕСЬ ТОЛЬКО СОБИРАЕТ МОДУЛИ
//
//   relay.h      — пины каналов и их положения;
//   sensors.h    — DHT22;
//   radio.h      — вход в сеть и удержание связи;
//   identity.h   — ключ платы и признак её владельца;
//   claim.h      — окно просьбы о хозяине;
//   settings.h   — действующие настройки сети;
//   transport.h  — дозвон до сервера и кадры;
//   commands.h   — разбор кадров сервера;
//   config_store — флеш-память платы;
//   provisioning — точка доступа для первичной настройки.
//
// Чтение и запись JSON делает ArduinoJson: он же следит за экранированием строк и не
// берёт для этого кучу — документ живёт на стеке в фиксированном объёме.
//
// НИЧЕГО НЕ ЗАШИТО
//
// Ни имени сети, ни пароля, ни адреса сервера в этом коде нет: плата узнаёт их от
// своего владельца — со страницы на собственной точке доступа или кадром
// SET_NETWORK — и хранит в памяти чипа.
//
// ИНТЕРФЕЙС ЖИВЁТ НА СЕРВЕРЕ
//
// Плата не раздаёт веб-интерфейс и не проксирует чужие HTTP-запросы: на
// однокристальной микросхеме с сорока килобайтами живой памяти это выходило в
// nginx, который к тому же не мог показать то, чего сам не знает. Готовый
// интерфейс отдаёт бэкенд (presentation/web), а плата остаётся чистым драйвером.
//
// ВАЖНО ПРО ПИНЫ
//
// D1..D6 (GPIO5, 4, 0, 2, 14, 12) — шесть каналов реле, D7 (GPIO13) — DATA
// датчика DHT22. GPIO0 и GPIO2 — бутстрап-пины: их состояние при подаче питания
// решает, уйдёт ли чип в загрузчик. Поэтому при старте пины каналов держатся
// INPUT_PULLUP и переходят в OUTPUT уже после загрузчика, а зажатая при включении
// кнопка FLASH (тот же GPIO0, канал 3) читается ровно один раз — в relaysBegin().
//
// Реле модулей активны низким уровнем: LOW замыкает контакт, HIGH отпускает.
// ============================================================================

#include <Arduino.h>

#include "claim.h"
#include "commands.h"
#include "identity.h"
#include "provisioning.h"
#include "radio.h"
#include "relay.h"
#include "sensors.h"
#include "settings.h"
#include "transport.h"

namespace {

/** Страница первичной настройки: одна на плату, поднимается по нужде. */
Provisioning provisioning;

/**
 * @brief Заполняет состояние платы для транспорта.
 *
 * Транспорт не знает ни про пины, ни про датчики: он получает готовое состояние и
 * кладёт его в кадр. Положения каналов идут массивом булевых значений, а не строкой.
 *
 * @param out Куда ложится состояние.
 */
void boardStatus(BoardStatus *out) {
    relaysSnapshot(out->relays, BOARD_RELAY_LIMIT);
    out->relayCount = RELAY_COUNT;
    out->temperature = sensorsTemperature();
    out->humidity = sensorsHumidity();
    out->askingForOwner = claimWindowOpen();
}

/**
 * @brief Поднимает точку доступа и ждёт, пока владелец введёт сеть.
 */
void startProvisioning() {
    provisioning.begin();
}

/**
 * @brief Запускает всё, что имеет смысл только на плате, которая в сети.
 */
void startService() {
    sensorsRead();
    if (sensorsReady()) {
        Serial.printf("[dht] %.1f C %.1f %%\n", sensorsTemperature(), sensorsHumidity());
    } else {
        Serial.println("[dht] no reading yet, check wiring of D7");
    }

    // Кнопка FLASH тянет GPIO0 к земле, а на этой разводке тот же пин — канал 3,
    // поэтому зажатая при включении питания кнопка и просит хозяина сразу. Флаг во
    // флеше — только кеш последнего ответа сервера: даже считающая себя привязанной
    // плата начнёт искать хозяина заново, стоит серверу сказать, что ключа он не
    // знает.
    if (relaysFlashHeld()) {
        identityForgetOwner();
        claimOpen();
        Serial.println("[claim] FLASH held at boot, opening the claim window");
    } else if (identityHasOwner()) {
        Serial.println("[claim] flash says this board is owned, waiting for the server");
    } else {
        claimOpen();
        Serial.println("[claim] never provisioned, opening the claim window");
    }

    transportBegin(boardStatus, commandsHandle);
    Serial.printf("[boot] free heap %u\n", ESP.getFreeHeap());
}

/**
 * @brief Обслуживает страницу настройки, пока плата ждёт сеть.
 *
 * @return True, пока настройка ещё нужна: главный цикл тогда ничего больше не делает.
 */
bool serviceProvisioning() {
    if (!provisioning.isActive()) {
        return false;
    }
    provisioning.loop();

    NetworkConfig submitted{};
    if (!provisioning.takeResult(submitted)) {
        return true;
    }
    settingsSave(submitted);
    provisioning.stop();

    if (radioJoin(RADIO_JOIN_TIMEOUT_MS)) {
        startService();
    } else {
        Serial.println("[wifi] the new network is unreachable, starting the setup access point");
        startProvisioning();
    }
    return true;
}

}  // namespace

void setup() {
    Serial.begin(115200);
    delay(200);
    Serial.println();
    Serial.println("[boot] smart home esp8266 firmware");
    Serial.printf("[boot] free heap %u\n", ESP.getFreeHeap());

    identityBegin();
    relaysBegin();
    sensorsBegin();

    if (!settingsLoad()) {
        // Плату никогда не настраивали: вместо попытки достучаться до сервера,
        // адреса которого она не знает, плата просит настроить себя.
        Serial.println("[wifi] no network, starting the setup access point");
        startProvisioning();
        return;
    }

    if (!radioJoin(RADIO_JOIN_TIMEOUT_MS)) {
        // Сеть исчезла или пароль испорчен. Единственный путь вперёд — снова
        // впустить владельца, поэтому точка доступа поднимается ещё раз.
        Serial.println("[wifi] the network is unreachable, starting the setup access point");
        startProvisioning();
        return;
    }

    startService();
}

void loop() {
    if (serviceProvisioning()) {
        return;
    }
    if (!radioKeepAlive()) {
        return;
    }
    transportLoop();
    sensorsRead();
    transportSendTelemetry();
    claimService();
}
