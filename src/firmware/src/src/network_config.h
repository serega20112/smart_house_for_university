/**
 * @file network_config.h
 * @brief The network a board belongs to and the server it reports to.
 *
 * Every board learns these values from the person who owns it: the board asks
 * for them on its own access point, keeps them in its own flash and never asks
 * again. The same binary is therefore flashed on every board and nobody opens
 * the IDE to write a password into it.
 *
 * The type is an aggregate of fixed character arrays on purpose. A board that
 * joins a network allocates memory for it, and on this chip a heap that moves
 * around ends in a crash with Exception (29) LoadStoreError.
 */

#pragma once

#include <Arduino.h>

/** Maximum length of a network name including the terminating zero. */
static const size_t NETWORK_SSID_SIZE = 33;

/** Maximum length of a network password including the terminating zero. */
static const size_t NETWORK_PASSWORD_SIZE = 65;

/** Maximum length of a numeric address including the terminating zero. */
static const size_t NETWORK_HOST_SIZE = 16;

/** Maximum length of the path of the board socket including the zero. */
static const size_t NETWORK_PATH_SIZE = 24;

/** Port of the interface of the server the board talks to. */
static const uint16_t DEFAULT_SERVER_PORT = 8000;

/** Port of the board socket of the server, one above the ordinary one. */
static const uint16_t DEFAULT_SOCKET_PORT = DEFAULT_SERVER_PORT + 1;

/** Path of the board socket of the server. */
static const char DEFAULT_SOCKET_PATH[] = "/ws/board";

/**
 * @brief Everything a board needs to reach its server.
 */
struct NetworkConfig {
    /** Name of the network the board joins. */
    char ssid[NETWORK_SSID_SIZE];

    /** Password of that network, empty for an open one. */
    char password[NETWORK_PASSWORD_SIZE];

    /** Numeric address of the server the board reports to. */
    char serverHost[NETWORK_HOST_SIZE];

    /** Port of the interface of that server. */
    uint16_t serverPort;

    /** Port of the board socket of that server. */
    uint16_t socketPort;

    /** Path of the board socket of that server. */
    char socketPath[NETWORK_PATH_SIZE];

    /** Whether the person who owns the board already filled this in. */
    bool provisioned;
};

/**
 * @brief Report whether the values are enough to reach the server.
 *
 * @param config Configuration to inspect.
 * @return True when the network and the server are both named.
 */
inline bool networkConfigIsValid(const NetworkConfig &config) {
    return config.ssid[0] != '\0' && config.serverHost[0] != '\0';
}

/**
 * @brief Report whether the address of the server is a numeric one.
 *
 * The board resolves a name with WiFi.hostByName, which is unreliable on this
 * chip, so only a numeric address is accepted.
 *
 * @param host Address to inspect.
 * @return True when the address can be read as an IP address.
 */
inline bool networkHostIsNumeric(const char *host) {
    IPAddress parsed;
    return parsed.fromString(host);
}
