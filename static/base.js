/* ── 全局基础功能：主题、时钟、天气 ──────── */

(function() {
    var saved = localStorage.getItem('theme');
    if (saved === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        document.getElementById('themeLabel').textContent = '浅色';
    }
})();

var WEEK_NAMES = ['日', '一', '二', '三', '四', '五', '六'];
var WX_CODES = {
    0: '☀️ 晴', 1: '🌤 少云', 2: '⛅ 多云', 3: '☁️ 阴',
    45: '🌫 雾', 48: '🌫 雾',
    51: '🌦 小毛毛雨', 53: '🌦 毛毛雨', 55: '🌦 大毛毛雨',
    56: '🌧 冻毛毛雨', 57: '🌧 冻毛毛雨',
    61: '🌦 小雨', 63: '🌧 中雨', 65: '🌧 大雨',
    66: '🌧 冻雨', 67: '🌧 冻雨',
    71: '🌨 小雪', 73: '🌨 中雪', 75: '❄️ 大雪',
    77: '❄️ 雪粒',
    80: '🌦 阵雨', 81: '🌧 中阵雨', 82: '🌧 大阵雨',
    85: '🌨 小阵雪', 86: '❄️ 大阵雪',
    95: '⛈ 雷暴', 96: '⛈ 雷暴+冰雹', 99: '⛈ 雷暴+冰雹',
};

function updateClock() {
    var now = new Date();
    var pad = function(n) { return n < 10 ? '0' + n : n; };
    var s = now.getFullYear() + '-' + pad(now.getMonth()+1) + '-' + pad(now.getDate())
          + ' 周' + WEEK_NAMES[now.getDay()] + ' '
          + pad(now.getHours()) + ':' + pad(now.getMinutes());
    document.getElementById('headerDatetime').textContent = s;
}

function fetchWeather() {
    var cached = sessionStorage.getItem('wx_weather');
    if (cached) {
        try {
            var c = JSON.parse(cached);
            if (Date.now() - c.ts < 1800000) {
                document.getElementById('headerWeather').textContent = c.text;
                return;
            }
        } catch(_) {}
    }
    fetch('https://api.open-meteo.com/v1/forecast?latitude=31.49&longitude=120.31&current_weather=true&timezone=Asia/Shanghai')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            var cw = d.current_weather;
            var code = cw.weathercode;
            var temp = Math.round(cw.temperature);
            var label = WX_CODES[code] || '🌡 ' + code;
            var txt = label + ' ' + temp + '°C';
            document.getElementById('headerWeather').textContent = txt;
            sessionStorage.setItem('wx_weather', JSON.stringify({text: txt, ts: Date.now()}));
        })
        .catch(function() {
            document.getElementById('headerWeather').textContent = '🌡 --°C';
        });
}

function toggleTheme() {
    var html = document.documentElement;
    var label = document.getElementById('themeLabel');
    if (html.getAttribute('data-theme') === 'light') {
        html.setAttribute('data-theme', 'dark');
        label.textContent = '深色';
        localStorage.setItem('theme', 'dark');
    } else {
        html.setAttribute('data-theme', 'light');
        label.textContent = '浅色';
        localStorage.setItem('theme', 'light');
    }
}

updateClock();
setInterval(updateClock, 30000);
fetchWeather();
