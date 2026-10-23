/**
 * @file setup_page.h
 * @brief The page the board serves while it waits to be set up.
 *
 * The page is stored in the flash of the chip and is served from the board's own
 * access point. It is deliberately tiny: the board answers it from a few
 * kilobytes of memory while the radio is busy, and every extra byte of markup is
 * a byte the socket does not get.
 */

#pragma once

static const char SETUP_PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Настройка платы</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070a0f;color:#e8eef7;font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:15px;line-height:1.5;padding:18px 14px 40px}
.wrap{max-width:460px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
h1{font-size:20px;font-weight:600;letter-spacing:-.02em}
p.sub{color:#7b8a9e;font-size:13px}
.card{background:#11161f;border:1px solid #222c3a;border-radius:16px;padding:15px}
label{display:block;margin-bottom:12px}
span.lab{display:block;color:#7b8a9e;font-size:12px;margin-bottom:5px;text-transform:uppercase;letter-spacing:.06em}
input{width:100%;padding:11px 12px;border-radius:11px;border:1px solid #222c3a;background:#070a0f;color:#e8eef7;font:inherit;outline:none}
input:focus{border-color:#4c9aff;box-shadow:0 0 0 3px rgba(76,154,255,.14)}
.row{display:flex;gap:10px}
.row>label{flex:1}
button{width:100%;padding:13px;border:none;border-radius:12px;background:#4c9aff;color:#04121f;font:inherit;font-weight:600;cursor:pointer}
button.ghost{background:#161d28;border:1px solid #222c3a;color:#e8eef7;font-weight:500}
.note{color:#7b8a9e;font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <div>
    <h1>Настройка платы</h1>
    <p class="sub">Введите данные домашней сети и адрес сервера. Плата сохранит их в своей памяти и отключит точку доступа.</p>
  </div>
  <form class="card" method="POST" action="/setup">
    <label>
      <span class="lab">Сеть</span>
      <input name="ssid" autocomplete="off" required>
    </label>
    <label>
      <span class="lab">Пароль</span>
      <input name="password" type="password" autocomplete="off">
    </label>
    <label>
      <span class="lab">Адрес сервера</span>
      <input name="host" value="192.168.1.10" required>
    </label>
    <div class="row">
      <label>
        <span class="lab">Порт сервера</span>
        <input name="server_port" value="8000">
      </label>
      <label>
        <span class="lab">Порт платы</span>
        <input name="socket_port" value="8001">
      </label>
    </div>
    <label>
      <span class="lab">Путь платы</span>
      <input name="socket_path" value="/ws/board">
    </label>
    <button type="submit">Сохранить и подключиться</button>
  </form>
  <p class="note">Плата запомнит эти данные и больше не спросит их. Сменить сеть можно позже в панели сервера.</p>
</div>
</body>
</html>
)HTML";

static const char SETUP_DONE_PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Плата настроена</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#070a0f;color:#e8eef7;font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:15px;line-height:1.5;padding:18px 14px 40px}
.wrap{max-width:460px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
h1{font-size:20px;font-weight:600}
p{color:#7b8a9e;font-size:13px}
.card{background:#11161f;border:1px solid #222c3a;border-radius:16px;padding:15px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Плата настроена</h1>
  <div class="card">
    <p>Данные сохранены. Плата подключается к сети и отключает точку доступа. Дальше откройте панель сервера и заберите плату себе.</p>
  </div>
</div>
</body>
</html>
)HTML";
