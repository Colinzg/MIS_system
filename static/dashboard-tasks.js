/* ── 调度面板 — 任务列表、筛选、拖拽分配 ── */

function toggleFlight(el) {
    var body = el.parentElement.querySelector('.fcard-body');
    var arrow = el.querySelector('.fcard-arrow');
    if (body.style.display === 'block') {
        body.style.display = 'none';
        arrow.textContent = '▶';
    } else {
        body.style.display = 'block';
        arrow.textContent = '▼';
    }
}

function filterTasks() {
    var type = document.getElementById('filterType').value;
    document.querySelectorAll('.fcard').forEach(function(c) {
        if (type) {
            var tasks = c.querySelectorAll('.ftask');
            var hasMatch = false;
            tasks.forEach(function(t) {
                var match = t.dataset.type === type;
                t.style.display = match ? '' : 'none';
                if (match) hasMatch = true;
            });
            c.style.display = hasMatch ? '' : 'none';
            if (hasMatch) {
                c.querySelector('.fcard-body').style.display = 'block';
                c.querySelector('.fcard-arrow').textContent = '▼';
            }
        } else {
            c.style.display = '';
            c.querySelector('.fcard-body').style.display = 'none';
            c.querySelector('.fcard-arrow').textContent = '▶';
            c.querySelectorAll('.ftask').forEach(function(t) { t.style.display = ''; });
        }
    });
}

function expandAll() {
    var btn = document.querySelector('.sidebar-expand-btn');
    var allExpanded = true;
    document.querySelectorAll('.fcard').forEach(function(c) {
        if (c.style.display !== 'none') {
            var body = c.querySelector('.fcard-body');
            if (body.style.display !== 'block') allExpanded = false;
        }
    });
    var expand = !allExpanded;
    document.querySelectorAll('.fcard').forEach(function(c) {
        if (c.style.display !== 'none') {
            var body = c.querySelector('.fcard-body');
            var arrow = c.querySelector('.fcard-arrow');
            body.style.display = expand ? 'block' : 'none';
            arrow.textContent = expand ? '▼' : '▶';
        }
    });
    btn.textContent = expand ? '全部收起' : '全部展开';
}

/* ── 拖拽分配车辆 ──────────────────────── */
function onDragStart(e) {
    var el = e.target.closest('[data-vehicle-id]');
    if (!el) return;
    if (!el.classList.contains('vtype-item')) return;
    var data = {
        vehicle_id: el.dataset.vehicleId,
        vehicle_type: el.dataset.vehicleType,
        vehicle_plate: el.dataset.vehiclePlate,
    };
    e.dataTransfer.setData('text/plain', JSON.stringify(data));
    e.dataTransfer.effectAllowed = 'move';
    el.classList.add('dragging');
}

document.addEventListener('dragend', function(e) {
    document.querySelectorAll('.dragging').forEach(function(el) {
        el.classList.remove('dragging');
    });
    document.querySelectorAll('.ftask.drop-target').forEach(function(el) {
        el.classList.remove('drop-target');
    });
});

function onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    e.currentTarget.classList.add('drop-target');
}

function onDragLeave(e) {
    e.currentTarget.classList.remove('drop-target');
}

function onDrop(e) {
    e.preventDefault();
    var card = e.currentTarget;
    card.classList.remove('drop-target');

    var raw = e.dataTransfer.getData('text/plain');
    if (!raw) return;
    var veh;
    try { veh = JSON.parse(raw); } catch(_) { return; }

    var taskId = card.dataset.taskId;
    if (!taskId) return;

    // 车型匹配检查
    var cardType = card.dataset.type;
    if (cardType && veh.vehicle_type !== cardType) {
        showFlash('error', '车型不匹配：需要 ' + cardType + '，拖拽的是 ' + veh.vehicle_type);
        return;
    }

    fetch('/api/assign-task', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({task_id: parseInt(taskId), vehicle_id: parseInt(veh.vehicle_id)}),
    })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (resp.ok) {
            showFlash('success', '已分配 ' + veh.vehicle_plate + ' → 任务 #' + taskId);
            sessionStorage.setItem('filterType', document.getElementById('filterType').value);
            setTimeout(function() { location.reload(); }, 800);
        } else {
            showFlash('error', resp.error || '分配失败');
        }
    })
    .catch(function() {
        showFlash('error', '网络错误，请重试');
    });
}

/* ── Toast 提示 ─────────────────────────── */
function showFlash(category, msg) {
    var container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    var div = document.createElement('div');
    div.className = 'toast toast-' + category;
    div.textContent = msg;
    container.appendChild(div);
    setTimeout(function() {
        div.style.opacity = '0';
        div.style.transform = 'translateX(80px)';
        setTimeout(function() { div.remove(); }, 300);
    }, 3000);
}

/* ── 自动分配 ───────────────────────────── */
function autoAssign() {
    var btn = document.querySelector('.sidebar-auto-btn');
    btn.disabled = true;
    btn.textContent = '分配中...';
    fetch('/api/auto-assign', {method: 'POST'})
    .then(function(r) {
        if (!r.ok) return r.text().then(function(t) { throw new Error(t || '服务端错误'); });
        return r.json();
    })
    .then(function(resp) {
        if (resp.ok) {
            showFlash('success', '已分配 ' + resp.assigned + ' 个任务，失败 ' + resp.errors + ' 个');
            setTimeout(function() { location.reload(); }, 1000);
        } else {
            showFlash('error', '自动分配失败');
            btn.disabled = false;
            btn.textContent = '自动分配';
        }
    })
    .catch(function(err) {
        showFlash('error', '请求失败：' + (err.message || '网络错误'));
        btn.disabled = false;
        btn.textContent = '自动分配';
    });
}

/* ── 页面初始化 ─────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
    renderAirportMap('airport-map');
    var savedType = sessionStorage.getItem('filterType');
    if (savedType) document.getElementById('filterType').value = savedType;
    if (savedType) filterTasks();
    sessionStorage.removeItem('filterType');
});
