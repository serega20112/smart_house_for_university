/**
 * @file provisioning.h
 * @brief The access point the board raises until it is told where to go.
 *
 * A board that has never been set up knows neither the network nor the server,
 * so it raises an access point of its own and serves a small page from it. The
 * person walks up to the board with a phone, joins that access point, fills in
 * the form and the board has everything it needs: the values are written into its
 * own flash, it joins the network and the access point disappears.
 *
 * The page is served from the soft access point, so the board needs no name
 * server, no address of its own and nothing from the outside world. That is the
 * whole point of the arrangement: a board bought in a shop works without anyone
 * typing a password into a file before flashing it.
 */

#pragma once

#include <Arduino.h>
#include <ESP8266WebServer.h>
#include <memory>

#include "network_config.h"

/** Port the setup page is served on. */
static const uint16_t SETUP_PORT = 80;

/** Length of the name of the access point including the terminating zero. */
static const size_t ACCESS_POINT_NAME_SIZE = 32;

/**
 * @brief The access point and the page that configures the board through it.
 */
class Provisioning {
   public:
    /** Prepare the board for the setup.
     *
     * Returns:
     *     None.
     */
    void begin();

    /** Serve the page and the form.
     *
     * Called from the main loop as often as possible: the radio is the only
     * thing the board can do while it waits, and a person standing next to it
     * expects the page to appear at once.
     *
     * Returns:
     *     None.
     */
    void loop();

    /** Stop serving and put the access point away.
     *
     * Returns:
     *     None.
     */
    void stop();

    /** Return whether the board is waiting to be set up.
     *
     * Returns:
     *     bool: True while the access point is up.
     */
    bool isActive() const { return _active; }

    /** Return the configuration the person filled in.
     *
     * The value is only valid once the form has been sent, which the caller
     * learns from the return value of this method.
     *
     * Returns:
     *     bool: True when a form was sent and accepted.
     */
    bool takeResult(NetworkConfig &out);

   private:
    /** Send the page with the form.
     *
     * Returns:
     *     None.
     */
    void servePage();

    /** Read the form and store what it says.
     *
     * Returns:
     *     None.
     */
    void handleSubmit();

    /** Read one field of the form into a fixed buffer.
     *
     * @param name Name of the field.
     * @param out Buffer the value is copied into.
     * @param capacity Size of that buffer.
     * @return The number of characters copied.
     */
    size_t readField(const char *name, char *out, size_t capacity);

    /** Read one numeric field of the form.
     *
     * @param name Name of the field.
     * @param fallback Value used when the field is empty or malformed.
     * @return The number the field carries.
     */
    uint16_t readNumber(const char *name, uint16_t fallback);

    // The server lives only while the board is being set up. It is a heavy
    // object on a chip with forty kilobytes of heap, and the board needs that
    // heap for the socket the moment the setup is over.
    std::unique_ptr<ESP8266WebServer> _server;
    bool _active{false};
    bool _submitted{false};
    NetworkConfig _result{};
};
