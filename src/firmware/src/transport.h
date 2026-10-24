/**
 * @file transport.h
 * @brief Дозвон платы до сервера: WebSocket-клиент и её кадры.
 *
 * Сервер слушает, а плата звонит сама: так плата из любой домашней сети достает
 * бэкенд на удалённой машине, и входящих соединений от неё не требуется.
 *
 * Транспорт не знает ни про реле, ни про датчики: состояние ему отдаёт поставщик,
 * который зарегистрирован у того, кто эти органы дома и водит. Кадры собирает
 * ArduinoJson — на стеке, без аллокаций в куче и с корректным экранированием строк.
 */

#pragma once

#include <Arduino.h>

/** Версия протокола, о которой договорились плата и сервер. */
static const int PROTOCOL_VERSION = 4;

/** Версия прошивки, которую плата называет сама. */
static const char FIRMWARE_VERSION[] = "1.5.0";

/**
 * Сколько положений каналов транспорт готов принять от поставщика состояния.
 *
 * Транспорт держит это со своим пределом, чтобы не знать про relay.h: плат с большим
 * числом каналов протокол не предполагает.
 */
static const uint8_t BOARD_RELAY_LIMIT = 8;

/** Размер буфера одного кадра: handshake несёт ключ, все каналы и имя сети. */
static const size_t FRAME_SIZE = 512;

/** Сколько раз в секунду плата сама шлёт показания. */
static const unsigned long TELEMETRY_INTERVAL_MS = 5000;

/** Через сколько плата снова звонится, если дозвониться не удалось. */
static const unsigned long SOCKET_RETRY_MS = 3000;

/**
 * @brief Состояние платы, которое транспорт кладёт в кадры.
 *
 * - `relays` — положения каналов по порядку, не больше BOARD_RELAY_LIMIT;
 * - `relayCount` — сколько элементов relays действительно заполнено;
 * - `temperature` — температура или NaN, если датчик молчит;
 * - `humidity` — влажность или NaN, если датчик молчит;
 * - `askingForOwner` — открыто ли окно просьбы о хозяине.
 */
struct BoardStatus {
    bool relays[BOARD_RELAY_LIMIT];
    uint8_t relayCount;
    float temperature;
    float humidity;
    bool askingForOwner;
};

/**
 * @brief Заполняет состояние платы; его регистрирует тот, кто водит органами дома.
 */
typedef void (*BoardStatusProvider)(BoardStatus *out);

/**
 * @brief Принимает один текстовый кадр сервера; его регистрирует разбор команд.
 */
typedef void (*BoardCommandHandler)(const char *json);

/**
 * @brief Запускает дозвон до сервера.
 *
 * @param status Поставщик состояния, которое ложится в кадры.
 * @param onCommand Обработчик команд сервера.
 */
void transportBegin(BoardStatusProvider status, BoardCommandHandler onCommand);

/**
 * @brief Обслуживает сокет: читает пришедшее и держит связь.
 */
void transportLoop();

/**
 * @brief Сообщает, есть ли соединение с сервером.
 *
 * @return True, когда кадр уйдёт прямо сейчас.
 */
bool transportConnected();

/**
 * @brief Шлёт серверу все положения каналов и показания датчиков.
 */
void transportSendState();

/**
 * @brief Шлёт периодические показания без состояния реле.
 */
void transportSendTelemetry();

/**
 * @brief Подтверждает выполнение команды.
 *
 * @param commandId Идентификатор команды из кадра сервера.
 */
void transportSendAck(const char *commandId);

/**
 * @brief Сообщает серверу, что команду выполнить не удалось.
 *
 * @param code Машинночитаемая причина отказа.
 * @param message Пояснение человеческими словами.
 */
void transportSendError(const char *code, const char *message);

/**
 * @brief Разрывает соединение: следующим дозвоном плата придёт с новыми данными.
 *
 * @param retryAfterMs Через сколько секунд стоит позвониться снова.
 */
void transportRedial(unsigned long retryAfterMs);
