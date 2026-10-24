/**
 * @file config_store.cpp
 * @brief Чтение и запись настроек, которые плата хранит у себя во флеше.
 */

#include "config_store.h"

#include <EEPROM.h>
#include <string.h>

namespace {

/** Смещение имени сети внутри блока сети. */
const size_t SSID_OFFSET = NETWORK_OFFSET;

/** Смещение пароля сети внутри блока сети. */
const size_t PASSWORD_OFFSET = SSID_OFFSET + NETWORK_SSID_SIZE;

/** Смещение адреса сервера внутри блока сети. */
const size_t HOST_OFFSET = PASSWORD_OFFSET + NETWORK_PASSWORD_SIZE;

/** Смещение порта интерфейса сервера внутри блока сети. */
const size_t SERVER_PORT_OFFSET = HOST_OFFSET + NETWORK_HOST_SIZE;

/** Смещение порта сокета сервера внутри блока сети. */
const size_t SOCKET_PORT_OFFSET = SERVER_PORT_OFFSET + sizeof(uint16_t);

/** Смещение пути сокета внутри блока сети. */
const size_t SOCKET_PATH_OFFSET = SOCKET_PORT_OFFSET + sizeof(uint16_t);

/** Смещение признака того, что плату настроили. */
const size_t PROVISIONED_OFFSET = SOCKET_PATH_OFFSET + NETWORK_PATH_SIZE;

/**
 * @brief Пишет один байт, только если он отличается от лежащего в памяти.
 *
 * @param offset Куда байт должен лечь.
 * @param value Значение для записи.
 * @return True, когда запись в память действительно понадобилась.
 */
bool writeByteIfChanged(size_t offset, uint8_t value) {
    if (EEPROM.read(offset) == value) {
        return false;
    }
    EEPROM.write(offset, value);
    return true;
}

/**
 * @brief Читает строку фиксированной длины из флеш-памяти.
 *
 * @param offset Где строка начинается.
 * @param out Буфер, куда строка копируется.
 * @param capacity Размер этого буфера.
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
 * @brief Пишет строку во флеш-память, не трогая неизменившиеся байты.
 *
 * @param offset Где строка начинается.
 * @param value Строка для сохранения.
 * @param capacity Размер поля, в которое она кладётся.
 * @return True, когда хотя бы один байт поля изменился.
 */
bool writeString(size_t offset, const char *value, size_t capacity) {
    bool changed = false;
    size_t index = 0;
    while (index + 1 < capacity && value[index] != '\0') {
        if (writeByteIfChanged(offset + index, static_cast<uint8_t>(value[index]))) {
            changed = true;
        }
        index++;
    }
    return writeByteIfChanged(offset + index, 0) || changed;
}

/**
 * @brief Читает порт из флеш-памяти.
 *
 * @param offset Где порт начинается.
 * @return Сохранённый порт.
 */
uint16_t readPort(size_t offset) {
    uint8_t low = EEPROM.read(offset);
    uint8_t high = EEPROM.read(offset + 1);
    return static_cast<uint16_t>(low | (high << 8));
}

/**
 * @brief Пишет порт во флеш-память, не трогая неизменившиеся байты.
 *
 * @param offset Где порт начинается.
 * @param value Порт для сохранения.
 * @return True, когда хотя бы один байт изменился.
 */
bool writePort(size_t offset, uint16_t value) {
    bool changed = writeByteIfChanged(offset, static_cast<uint8_t>(value & 0xFF));
    return writeByteIfChanged(offset + 1, static_cast<uint8_t>((value >> 8) & 0xFF)) || changed;
}

/**
 * @brief Отдаёт флеш-память обратно, если в неё что-то легло.
 *
 * commit() перезаписывает сектор целиком, поэтому вызывается он ровно один раз и
 * только после реальных изменений: иначе каждое переподключение платы стирало бы
 * ресурс памяти впустую.
 *
 * @param changed True, если между чтением и сейчас что-то изменилось.
 */
void commitIfChanged(bool changed) {
    if (changed) {
        EEPROM.commit();
    }
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
    bool changed = false;
    size_t index = 0;
    while (key[index] != '\0') {
        if (writeByteIfChanged(DEVICE_KEY_OFFSET + index, static_cast<uint8_t>(key[index]))) {
            changed = true;
        }
        index++;
    }
    commitIfChanged(writeByteIfChanged(DEVICE_KEY_OFFSET + index, 0) || changed);
}

bool configStoreIsClaimed() {
    return EEPROM.read(CLAIMED_FLAG_OFFSET) == 1;
}

void configStoreSetClaimed(bool claimed) {
    commitIfChanged(writeByteIfChanged(CLAIMED_FLAG_OFFSET, claimed ? 1 : 0));
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
    bool changed = writeString(SSID_OFFSET, config.ssid, sizeof(config.ssid));
    changed = writeString(PASSWORD_OFFSET, config.password, sizeof(config.password)) || changed;
    changed = writeString(HOST_OFFSET, config.serverHost, sizeof(config.serverHost)) || changed;
    changed = writePort(SERVER_PORT_OFFSET, config.serverPort) || changed;
    changed = writePort(SOCKET_PORT_OFFSET, config.socketPort) || changed;
    changed = writeString(SOCKET_PATH_OFFSET, config.socketPath, sizeof(config.socketPath))
              || changed;
    commitIfChanged(writeByteIfChanged(PROVISIONED_OFFSET, config.provisioned ? 1 : 0) || changed);
}
