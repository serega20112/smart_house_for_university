/**
 * @file config_store.cpp
 * @brief Reading and writing the settings a board keeps in its own flash.
 */

#include "config_store.h"

#include <EEPROM.h>
#include <string.h>

namespace {

/** Offset of the network name inside the network block. */
const size_t SSID_OFFSET = NETWORK_OFFSET;

/** Offset of the network password inside the network block. */
const size_t PASSWORD_OFFSET = SSID_OFFSET + NETWORK_SSID_SIZE;

/** Offset of the server address inside the network block. */
const size_t HOST_OFFSET = PASSWORD_OFFSET + NETWORK_PASSWORD_SIZE;

/** Offset of the interface port of the server inside the network block. */
const size_t SERVER_PORT_OFFSET = HOST_OFFSET + NETWORK_HOST_SIZE;

/** Offset of the socket port of the server inside the network block. */
const size_t SOCKET_PORT_OFFSET = SERVER_PORT_OFFSET + sizeof(uint16_t);

/** Offset of the socket path inside the network block. */
const size_t SOCKET_PATH_OFFSET = SOCKET_PORT_OFFSET + sizeof(uint16_t);

/** Offset of the flag telling whether the board was set up. */
const size_t PROVISIONED_OFFSET = SOCKET_PATH_OFFSET + NETWORK_PATH_SIZE;

/**
 * @brief Copy a fixed size string out of the flash.
 *
 * @param offset Where the string starts.
 * @param out Buffer the string is copied into.
 * @param capacity Size of that buffer.
 * @return None.
 */
void readString(size_t offset, char *out, size_t capacity) {
    size_t index = 0;
    while (index + 1 < capacity) {
        uint8_t value = EEPROM.read(offset + index);
        if (value == 0 || value == 0xFF) {
            break;
        }
        out[index] = static_cast<char>(value);
        index++;
    }
    out[index] = '\0';
}

/**
 * @brief Write a string into the flash.
 *
 * @param offset Where the string starts.
 * @param value String to store.
 * @param capacity Size of the field the string is stored in.
 * @return None.
 */
void writeString(size_t offset, const char *value, size_t capacity) {
    size_t index = 0;
    while (index + 1 < capacity && value[index] != '\0') {
        EEPROM.write(offset + index, static_cast<uint8_t>(value[index]));
        index++;
    }
    EEPROM.write(offset + index, 0);
}

/**
 * @brief Read a port out of the flash.
 *
 * @param offset Where the port starts.
 * @return Port that was stored.
 */
uint16_t readPort(size_t offset) {
    uint8_t low = EEPROM.read(offset);
    uint8_t high = EEPROM.read(offset + 1);
    return static_cast<uint16_t>(low | (high << 8));
}

/**
 * @brief Write a port into the flash.
 *
 * @param offset Where the port starts.
 * @param value Port to store.
 * @return None.
 */
void writePort(size_t offset, uint16_t value) {
    EEPROM.write(offset, static_cast<uint8_t>(value & 0xFF));
    EEPROM.write(offset + 1, static_cast<uint8_t>((value >> 8) & 0xFF));
}

}  // namespace

void configStoreBegin() {
    EEPROM.begin(EEPROM_SIZE);
}

size_t configStoreReadDeviceKey(char *out, size_t capacity) {
    size_t index = 0;
    while (index + 1 < capacity) {
        uint8_t value = EEPROM.read(DEVICE_KEY_OFFSET + index);
        if (value == 0 || value == 0xFF) {
            break;
        }
        out[index] = static_cast<char>(value);
        index++;
    }
    out[index] = '\0';
    return index;
}

void configStoreWriteDeviceKey(const char *key) {
    size_t index = 0;
    while (key[index] != '\0') {
        EEPROM.write(DEVICE_KEY_OFFSET + index, static_cast<uint8_t>(key[index]));
        index++;
    }
    EEPROM.write(DEVICE_KEY_OFFSET + index, 0);
    EEPROM.commit();
}

bool configStoreIsClaimed() {
    return EEPROM.read(CLAIMED_FLAG_OFFSET) == 1;
}

void configStoreSetClaimed(bool claimed) {
    EEPROM.write(CLAIMED_FLAG_OFFSET, claimed ? 1 : 0);
    EEPROM.commit();
}

bool configStoreLoadNetwork(NetworkConfig &out) {
    readString(SSID_OFFSET, out.ssid, sizeof(out.ssid));
    readString(PASSWORD_OFFSET, out.password, sizeof(out.password));
    readString(HOST_OFFSET, out.serverHost, sizeof(out.serverHost));
    readString(SOCKET_PATH_OFFSET, out.socketPath, sizeof(out.socketPath));
    out.serverPort = readPort(SERVER_PORT_OFFSET);
    out.socketPort = readPort(SOCKET_PORT_OFFSET);
    out.provisioned = EEPROM.read(PROVISIONED_OFFSET) == 1;
    if (out.serverPort == 0) {
        out.serverPort = DEFAULT_SERVER_PORT;
    }
    if (out.socketPort == 0) {
        out.socketPort = DEFAULT_SOCKET_PORT;
    }
    if (out.socketPath[0] == '\0') {
        strcpy(out.socketPath, DEFAULT_SOCKET_PATH);
    }
    return out.provisioned;
}

void configStoreSaveNetwork(const NetworkConfig &config) {
    writeString(SSID_OFFSET, config.ssid, sizeof(config.ssid));
    writeString(PASSWORD_OFFSET, config.password, sizeof(config.password));
    writeString(HOST_OFFSET, config.serverHost, sizeof(config.serverHost));
    writePort(SERVER_PORT_OFFSET, config.serverPort);
    writePort(SOCKET_PORT_OFFSET, config.socketPort);
    writeString(SOCKET_PATH_OFFSET, config.socketPath, sizeof(config.socketPath));
    EEPROM.write(PROVISIONED_OFFSET, config.provisioned ? 1 : 0);
    EEPROM.commit();
}
