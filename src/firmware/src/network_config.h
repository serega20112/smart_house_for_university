/**
 * @file network_config.h
 * @brief Сеть, к которой относится плата, и сервер, которому она докладывает.
 *
 * Эти значения плата получает от своего владельца: спрашивает их сама на своей
 * точке доступа, хранит в памяти чипа и больше никогда не переспрашивает. Поэтому
 * одна и та же прошивка уходит всем, и никто не открывает IDE, чтобы вписать туда
 * пароль.
 *
 * Тип намеренно агрегат из фиксированных массивов знаков. Выход в сеть — это
 * аллокации, а на этой микросхеме куча, которая ходит туда-сюда, кончается
 * падением с Exception (29) LoadStoreError.
 */

#pragma once

#include <Arduino.h>

/** Наибольшая длина имени сети вместе с нулём. */
static const size_t NETWORK_SSID_SIZE = 33;

/** Наибольшая длина пароля сети вместе с нулём. */
static const size_t NETWORK_PASSWORD_SIZE = 65;

/** Наибольшая длина числового адреса вместе с нулём. */
static const size_t NETWORK_HOST_SIZE = 16;

/** Наибольшая длина пути сокета платы вместе с нулём. */
static const size_t NETWORK_PATH_SIZE = 24;

/** Порт интерфейса сервера, с которым говорит плата. */
static const uint16_t DEFAULT_SERVER_PORT = 8000;

/** Порт сокета платы на сервере: на единицу выше обычного. */
static const uint16_t DEFAULT_SOCKET_PORT = DEFAULT_SERVER_PORT + 1;

/** Путь сокета платы на сервере. */
static const char DEFAULT_SOCKET_PATH[] = "/ws/board";

/**
 * @brief Всё, что плате нужно, чтобы достать свой сервер.
 */
struct NetworkConfig {
    /** Имя сети, в которую плата входит. */
    char ssid[NETWORK_SSID_SIZE];

    /** Пароль этой сети, пустой для открытой. */
    char password[NETWORK_PASSWORD_SIZE];

    /** Числовой адрес сервера, которому плата докладывает. */
    char serverHost[NETWORK_HOST_SIZE];

    /** Порт интерфейса этого сервера. */
    uint16_t serverPort;

    /** Порт сокета платы на этом сервере. */
    uint16_t socketPort;

    /** Путь сокета платы на этом сервере. */
    char socketPath[NETWORK_PATH_SIZE];

    /** Заполнил ли уже владелец эти значения. */
    bool provisioned;
};

/**
 * @brief Сообщает, хватает ли значений, чтобы достать сервер.
 *
 * @param config Конфигурация, которую рассматривают.
 * @return True, когда названы и сеть, и сервер.
 */
inline bool networkConfigIsValid(const NetworkConfig &config) {
    return config.ssid[0] != '\0' && config.serverHost[0] != '\0';
}

/**
 * @brief Сообщает, числовой ли адрес сервера.
 *
 * Плата разрешает имя через WiFi.hostByName, что на этой микросхеме ненадёжно,
 * поэтому принимается только числовой адрес.
 *
 * @param host Адрес, который рассматривают.
 * @return True, когда адрес читается как IP.
 */
inline bool networkHostIsNumeric(const char *host) {
    IPAddress parsed;
    return parsed.fromString(host);
}
