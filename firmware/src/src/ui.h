// ============================================================================
// Embedded web interface, stored in flash and served by the board.
//
// The whole interface lives here as one compact page. It is far too small for
// any framework, which is exactly why it fits: no runtime, no dependencies and
// an instant first paint, even on a slow link.
//
// The page talks to the backend through this board. Every request goes to the
// board, the board forwards it to the backend and returns the answer, so the
// backend port is never exposed to the internet.
//
// Poll the state instead of opening a WebSocket: proxying one is not possible
// here, the board is already a WebSocket client of the backend itself. Two
// seconds is fast enough for a home interface and the load stays trivial.
// ============================================================================

#pragma once

static const char INDEX_HTML[] PROGMEM = R"HTML(<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#070a0f">
<title>Умный дом</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(900px 500px at 15% -10%,#10243d 0,transparent 60%),radial-gradient(700px 400px at 95% 0,#1a1030 0,transparent 55%),#070a0f;background-attachment:fixed;color:#e8eef7;font-family:system-ui,-apple-system,Segoe UI,sans-serif;font-size:15px;line-height:1.5;padding:20px 16px 44px;-webkit-font-smoothing:antialiased}
.wrap{max-width:520px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
h1{font-size:22px;font-weight:600;letter-spacing:-.02em}
h2{font-size:13px;color:#7b8a9e;font-weight:500;text-transform:uppercase;letter-spacing:.08em}
.sub{color:#7b8a9e;font-size:13px;margin-top:2px}
.card{background:linear-gradient(165deg,#11161f,#070a0f 130%);border:1px solid #222c3a;border-radius:18px;padding:16px}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;font-size:12px;border:1px solid transparent;white-space:nowrap}
.b-ok{color:#2fd48a;background:rgba(47,212,138,.1);border-color:rgba(47,212,138,.28)}
.b-bad{color:#ff5f6d;background:rgba(255,95,109,.1);border-color:rgba(255,95,109,.3)}
.b-warn{color:#ffb454;background:rgba(255,180,84,.1);border-color:rgba(255,180,84,.28)}
.b-idle{color:#7b8a9e;background:rgba(123,138,158,.1);border-color:rgba(123,138,158,.25)}
.b-head{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
.climate{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.metric{font-size:32px;font-weight:300;letter-spacing:-.03em;line-height:1.15;margin-top:6px}
.unit{font-size:.5em;color:#7b8a9e;vertical-align:super}
.note{color:#7b8a9e;font-size:12px;margin-top:6px}
.dev{position:relative;display:flex;flex-direction:column;gap:11px;padding:13px 15px;border-radius:14px;border:1px solid #222c3a;background:linear-gradient(160deg,#161d28,#070a0f 140%);overflow:hidden}
.dev+.dev{margin-top:10px}
.bar{position:absolute;inset:0 auto 0 0;width:3px;background:#7b8a9e}
.bar.on,.bar.cool{background:#2fd48a;box-shadow:0 0 14px rgba(47,212,138,.6)}
.bar.heat{background:#ffb454;box-shadow:0 0 14px rgba(255,180,84,.5)}
.bar.unavailable{background:#ff5f6d}
.dname{font-size:14px;font-weight:500}
.dmeta{color:#7b8a9e;font-size:11px;margin-top:1px}
.sw{position:relative;width:46px;height:26px;flex:none;border-radius:999px;border:1px solid #222c3a;background:rgba(255,255,255,.05);cursor:pointer}
.sw::after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:50%;background:#7b8a9e;transition:.2s}
.sw.on{background:rgba(76,154,255,.3);border-color:#4c9aff}
.sw.on::after{transform:translateX(20px);background:#fff}
.sw.dis{opacity:.4;pointer-events:none}
.modes{display:flex;gap:6px;flex-wrap:wrap}
.chip{padding:5px 11px;border-radius:999px;border:1px solid #222c3a;background:#161d28;color:#7b8a9e;font:inherit;font-size:12px;cursor:pointer}
.chip.on{color:#04121f;background:#4c9aff;border-color:transparent;font-weight:500}
.log{display:flex;flex-direction:column;gap:7px;max-height:230px;overflow-y:auto}
.bub{max-width:80%;padding:9px 13px;border-radius:14px;font-size:14px;word-break:break-word}
.me{align-self:flex-end;background:#4c9aff;color:#04121f;border-bottom-right-radius:4px}
.sys{align-self:flex-start;background:#161d28;border:1px solid #222c3a;border-bottom-left-radius:4px}
.sys.err{border-color:rgba(255,95,109,.4)}
.inp{display:flex;gap:7px;margin-top:11px}
input[type=text]{flex:1;min-width:0;padding:11px 13px;border-radius:12px;border:1px solid #222c3a;background:#070a0f;color:#e8eef7;font:inherit;outline:none}
input[type=text]:focus{border-color:#4c9aff;box-shadow:0 0 0 3px rgba(76,154,255,.14)}
button.send{padding:11px 16px;border-radius:12px;border:none;background:#4c9aff;color:#04121f;font:inherit;font-weight:500;cursor:pointer}
button.send:disabled{opacity:.5}
.empty{color:#7b8a9e;font-size:13px;padding:6px 0}
.lnk{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#7b8a9e}
.dt{width:7px;height:7px;border-radius:50%;background:#2fd48a;box-shadow:0 0 8px #2fd48a}
.dt.off{background:#ff5f6d;box-shadow:0 0 8px #ff5f6d;animation:pl 1.6s infinite}
@keyframes pl{50%{opacity:.35}}
</style>
</head>
<body>
<div class="wrap">
  <div>
    <h1>Умный дом</h1>
    <p class="sub" id="upd">подключение…</p>
  </div>
  <div class="card">
    <div class="row">
      <span class="lnk"><span class="dt" id="dt"></span><span id="lbl">связь с панелью</span></span>
    </div>
    <div class="b-head" id="bars"></div>
  </div>
  <div class="climate">
    <div class="card"><h2>Температура</h2><p class="metric" id="t">—</p><p class="note" id="tn"></p></div>
    <div class="card"><h2>Влажность</h2><p class="metric" id="h">—</p><p class="note" id="hn"></p></div>
  </div>
  <div class="card">
    <h2 style="margin-bottom:11px">Устройства</h2>
    <div id="devs"><p class="empty">Загрузка…</p></div>
  </div>
  <div class="card">
    <div class="row" style="margin-bottom:11px">
      <h2>Команды</h2>
      <span class="badge b-idle" id="auto">AUTO —</span>
    </div>
    <div class="log" id="log"></div>
    <div class="chips" style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">
      <button class="chip" onclick="say('включи свет')">включи свет</button>
      <button class="chip" onclick="say('выключи всё')">выключи всё</button>
      <button class="chip" onclick="say('сделай прохладнее')">прохладнее</button>
      <button class="chip" onclick="say('какая температура')">температура</button>
    </div>
    <form class="inp" onsubmit="return send(event)">
      <input type="text" id="cmd" placeholder="например: сделай прохладнее" autocomplete="off">
      <button class="send" id="go" type="submit">→</button>
    </form>
  </div>
</div>
<script>
var busy=false;
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function say(t){document.getElementById('cmd').value=t;document.getElementById('cmd').form.requestSubmit()}
function log(t,who){
  var l=document.getElementById('log'),e=el('div','bub '+(who==='me'?'me':'sys'),t);
  l.appendChild(e);l.scrollTop=l.scrollHeight;
}
async function api(path,opt){
  var r=await fetch('/api'+path,opt||{});
  if(!r.ok){var d=await r.json().catch(function(){return{}});throw new Error(d.detail||('ошибка '+r.status))}
  return r.json();
}
async function act(id,on){
  try{await api('/devices/'+id+'/'+(on?'on':'off'),{method:'POST'});load()}
  catch(e){log(e.message,'sys')}
}
async function mode(id,m){
  try{await api('/devices/'+id+'/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:m})});load()}
  catch(e){log(e.message,'sys')}
}
function render(s){
  document.getElementById('bars').innerHTML='';
  var b=el('span','badge b-ok','Backend: Online');document.getElementById('bars').appendChild(b);
  document.getElementById('bars').appendChild(el('span','badge '+(s.esp_online?'b-ok':'b-bad'),'ESP8266: '+(s.esp_online?'Online':'Offline')));
  if(s.manual_override)document.getElementById('bars').appendChild(el('span','badge b-warn','Ручное управление'));
  if(s.active_scenarios.length)document.getElementById('bars').appendChild(el('span','badge b-warn','Сценариев: '+s.active_scenarios.length));
  document.getElementById('t').innerHTML=s.temperature===null?'—':s.temperature.toFixed(1)+'<span class="unit">&deg;C</span>';
  document.getElementById('h').innerHTML=s.humidity===null?'—':s.humidity.toFixed(0)+'<span class="unit">%</span>';
  document.getElementById('tn').textContent='цель '+s.automation.target_temperature.toFixed(1)+'°C';
  document.getElementById('hn').textContent='цель '+s.automation.target_humidity.toFixed(0)+'%';
  document.getElementById('auto').textContent='AUTO '+(s.automation.enabled?'ON':'OFF');
  document.getElementById('auto').className='badge '+(s.automation.enabled?'b-ok':'b-idle');
  var box=document.getElementById('devs');box.innerHTML='';
  if(!s.devices.length){box.appendChild(el('p','empty','Устройства не заданы'))}
  var tone={ON:'b-ok',COOL:'b-ok',HEAT:'b-warn',OFF:'b-idle',UNAVAILABLE:'b-bad'};
  var txt={ON:'Включено',OFF:'Выключено',COOL:'Охлаждение',HEAT:'Нагрев',UNAVAILABLE:'Недоступно'};
  s.devices.forEach(function(d){
    var on=d.status==='ON'||d.status==='COOL'||d.status==='HEAT';
    var c=el('div','dev');
    c.appendChild(el('span','bar '+d.status.toLowerCase()));
    var top=el('div','row');
    var l=el('div');
    l.appendChild(el('div','dname',d.name));
    l.appendChild(el('div','dmeta','канал '+d.physical_channel));
    top.appendChild(l);
    top.appendChild(el('span','badge '+tone[d.status],txt[d.status]));
    c.appendChild(top);
    var modes=d.capabilities.filter(function(x){return x!=='OFF'});
    if(modes.length>1){
      var mc=el('div','modes');
      modes.forEach(function(m){
        var b=el('button','chip'+(d.status===m?' on':''),m==='ON'?'Вкл':m==='COOL'?'Охлаждение':m==='HEAT'?'Нагрев':'Выкл');
        if(d.status==='UNAVAILABLE')b.disabled=true;
        b.onclick=function(){mode(d.id,m)};
        mc.appendChild(b);
      });
      c.appendChild(mc);
    }
    var foot=el('div','row');
    foot.appendChild(el('span','dmeta',txt[d.status]));
    var sw=el('button','sw'+(on?' on':'')+(d.status==='UNAVAILABLE'?' dis':''));
    sw.onclick=function(){act(d.id,!on)};
    foot.appendChild(sw);
    c.appendChild(foot);
    box.appendChild(c);
  });
}
function fail(){
  document.getElementById('dt').className='dt off';
  document.getElementById('lbl').textContent='панель недоступна';
}
async function load(){
  try{var s=await api('/state');render(s);
    document.getElementById('upd').textContent='обновлено '+new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    document.getElementById('lbl').textContent='связь с панелью';
  }catch(e){fail()}
}
async function send(ev){
  ev.preventDefault();
  var i=document.getElementById('cmd'),t=i.value.trim();
  if(!t||busy)return false;
  busy=true;document.getElementById('go').disabled=true;
  i.value='';log(t,'me');
  try{var r=await api('/commands',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
    log(r.message,r.requires_clarification?'sys err':'sys');load()}
  catch(e){log(e.message,'sys err')}
  busy=false;document.getElementById('go').disabled=false;
  return false;
}
load();
setInterval(load,2000);
</script>
</body>
</html>
)HTML";
