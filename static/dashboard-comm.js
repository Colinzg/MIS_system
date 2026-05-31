/* ── 调度面板 — 车载终端通讯 ───────────── */

var COMM_VEHICLE_ID = null;
var COMM_LAST_TIME = null;
var COMM_POLL_ID = null;

var VSTATUS_MAP = {
    'IDLE': ['green', '空闲'],
    'ASSIGNED': ['yellow', '已分配'],
    'CONFIRMED': ['blue', '已确认'],
    'BUSY': ['purple', '工作中'],
    'REFUELING': ['orange', '回补中'],
    'MAINTENANCE': ['yellow', '维修中'],
};

function loadCommVehicles() {
    fetch('/api/comm/unread')
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (!resp.ok) return;
        var bar = document.getElementById('commVBar');
        bar.innerHTML = '';
        var totalUnread = 0;
        for (var vid in resp.unread) {
            var u = resp.unread[vid];
            totalUnread += u.unread;
            var item = document.createElement('div');
            item.className = 'comm-vitem' + (COMM_VEHICLE_ID == vid ? ' comm-vitem-active' : '');
            item.innerHTML =
                '<span class="comm-vitem-icon">' + (u.icon || '🚛') + '</span>' +
                '<span class="comm-vitem-info">' +
                    '<span class="comm-vitem-plate">' + u.plate + '</span>' +
                    '<span class="comm-vitem-status indicator indicator-' + (VSTATUS_MAP[u.status] ? VSTATUS_MAP[u.status][0] : 'gray') + '">' + (VSTATUS_MAP[u.status] ? VSTATUS_MAP[u.status][1] : u.status) + '</span>' +
                '</span>' +
                (u.unread > 0 ? '<span class="comm-vitem-badge">' + u.unread + '</span>' : '');
            item.onclick = function(id) { return function() { selectCommVehicle(id); }; }(parseInt(vid));
            bar.appendChild(item);
        }
        document.getElementById('unreadBadge').textContent = totalUnread + ' 待处理';
    });
}

function selectCommVehicle(vehicleId) {
    COMM_VEHICLE_ID = vehicleId;
    COMM_LAST_TIME = null;
    loadCommVehicles();
    var box = document.getElementById('commLogBox');
    box.innerHTML = '<div class="comm-empty">加载中...</div>';
    fetch('/api/comm/history?vehicle_id=' + vehicleId)
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (!resp.ok) return;
        box.innerHTML = '';
        resp.messages.forEach(function(m) { appendCommMsg(m); });
        if (resp.messages.length) {
            COMM_LAST_TIME = resp.messages[resp.messages.length - 1].created_at;
        }
        box.scrollTop = box.scrollHeight;
    });
    if (COMM_POLL_ID) clearInterval(COMM_POLL_ID);
    COMM_POLL_ID = setInterval(pollCommMessages, 4000);
}

function pollCommMessages() {
    if (!COMM_VEHICLE_ID) return;
    var url = '/api/comm/history?vehicle_id=' + COMM_VEHICLE_ID;
    if (COMM_LAST_TIME) url += '&since=' + encodeURIComponent(COMM_LAST_TIME);
    fetch(url)
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (!resp.ok || !resp.messages.length) return;
        resp.messages.forEach(function(m) { appendCommMsg(m); });
        COMM_LAST_TIME = resp.messages[resp.messages.length - 1].created_at;
    });
}

function appendCommMsg(msg) {
    var box = document.getElementById('commLogBox');
    if (box.querySelector('.comm-empty')) box.innerHTML = '';
    var div = document.createElement('div');
    div.className = 'comm-msg comm-msg-' + msg.sender.toLowerCase();
    var label = msg.sender === 'DISPATCH' ? '📡 调度中心' : '🚛 ' + (msg.vehicle_plate || '车辆');
    div.innerHTML = '<div class="comm-msg-meta">' + label + ' ' + msg.created_at + '</div>' +
                    '<div class="comm-msg-body">' + escapeHtml(msg.content) + '</div>';
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

function sendDispatch() {
    var input = document.getElementById('commInput');
    var content = input.value.trim();
    if (!content || !COMM_VEHICLE_ID) {
        if (!COMM_VEHICLE_ID) showFlash('error', '请先选择车辆');
        return;
    }
    input.value = '';
    fetch('/api/comm/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            vehicle_id: COMM_VEHICLE_ID,
            sender: 'DISPATCH',
            content: content,
        }),
    })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (resp.ok) appendCommMsg(resp.message);
        else showFlash('error', resp.error || '发送失败');
    });
}

function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
    loadCommVehicles();
    setInterval(loadCommVehicles, 5000);
});
