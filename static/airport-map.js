/**
 * 机场态势图 — D3.js 可视化
 *
 * 布局（俯视）：
 *   [=== T1 (A01-A08) ===]  [A-1] [塔台] [B-1]  [=== T2 (B01-B08) ===]
 *
 * 停机位和停车场坐标从 /api/map-data 加载，与 data/airport_display.json 同步。
 */

const MAP_W = 1000, MAP_H = 294;

// 上一轮渲染的航班完整信息，用于检测离场航班
var _prevFlightsMap = new Map();  // Map<id, flightObject>

// 状态 → 颜色
const STATUS_COLORS = {
  FLIGHT:  { SCHEDULED: '#3b82f6', ARRIVED: '#f59e0b', DEPARTED: '#22c55e', CANCELLED: '#ef4444' },
  VEHICLE: { IDLE: '#22c55e', ASSIGNED: '#eab308', BUSY: '#a855f7', REFUELING: '#f97316', MAINTENANCE: '#f59e0b' },
};

// 主渲染函数
function renderAirportMap(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = '';
  const svg = d3.select(`#${containerId}`)
    .append('svg')
    .attr('viewBox', `0 -14 ${MAP_W} 294`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('width', '100%')
    .style('height', 'auto');

  // 静态机场布局（背景、滑行道、航站楼、指北箭头；动态元素在 API 回调中渲染）

  svg.append('rect')
    .attr('x', 0).attr('y', -14).attr('width', MAP_W).attr('height', 294)
    .attr('fill', 'var(--map-bg, #1a1f2e)').attr('rx', 8);

  // 滑行道
  svg.append('rect')
    .attr('x', 10).attr('y', 58).attr('width', 980).attr('height', 6)
    .attr('fill', 'var(--map-taxiway, #334155)').attr('rx', 3);
  for (let x = 24; x < 990; x += 50) {
    svg.append('rect')
      .attr('x', x).attr('y', 60).attr('width', 20).attr('height', 2)
      .attr('fill', '#fbbf24').attr('rx', 1);
  }

  // 航站楼 A
  const tAG = svg.append('g');
  tAG.append('rect')
    .attr('x', 20).attr('y', 12).attr('width', 385).attr('height', 38)
    .attr('fill', 'var(--map-terminal, #1e3a5f)').attr('rx', 4);
  tAG.append('text')
    .attr('x', 212).attr('y', 37).attr('text-anchor', 'middle')
    .attr('fill', 'var(--map-text, #94a3b8)').attr('font-size', 13).attr('font-weight', 'bold')
    .text('T1 航站楼 - A 区');

  // 航站楼 B
  const tBG = svg.append('g');
  tBG.append('rect')
    .attr('x', 596).attr('y', 12).attr('width', 260).attr('height', 38)
    .attr('fill', 'var(--map-terminal, #1e3a5f)').attr('rx', 4);
  tBG.append('text')
    .attr('x', 726).attr('y', 37).attr('text-anchor', 'middle')
    .attr('fill', 'var(--map-text, #94a3b8)').attr('font-size', 13).attr('font-weight', 'bold')
    .text('T2 航站楼 - B 区');

  // 指北箭头
  const compassG = svg.append('g').attr('transform', 'translate(960, 28) rotate(70)');
  compassG.append('polygon')
    .attr('points', '0,-14 -5,4 0,-2 5,4')
    .attr('fill', '#ef4444');
  compassG.append('text')
    .attr('x', 0).attr('y', 8).attr('text-anchor', 'middle')
    .attr('fill', '#ef4444').attr('font-size', 7).attr('font-weight', 'bold')
    .text('北');

  // 数据绑定层
  const flightLayer = svg.append('g').attr('class', 'flight-layer');

  // 加载数据
  fetch('/api/map-data')
    .then(res => res.json())
    .then(data => {
      // 检测离场航班：上一轮存在但本轮消失的 → 触发起飞弹窗
      var currentIds = new Set((data.flights || []).map(function(f) { return f.id; }));
      if (_prevFlightsMap.size > 0) {
        _prevFlightsMap.forEach(function(flight, fid) {
          if (!currentIds.has(fid)) {
            showDeparturePopup(flight);
          }
        });
      }
      // 更新缓存：存储当前所有航班以便下一轮检测
      _prevFlightsMap.clear();
      (data.flights || []).forEach(function(f) {
        _prevFlightsMap.set(f.id, f);
      });

      // 停机位引导线 + 标签
      data.gates.forEach(g => {
        svg.append('line')
          .attr('x1', g.x).attr('y1', 67).attr('x2', g.x).attr('y2', 84)
          .attr('stroke', '#475569').attr('stroke-width', 0.5)
          .attr('stroke-dasharray', '2,3').attr('stroke-linecap', 'round');
        svg.append('circle')
          .attr('cx', g.x).attr('cy', 84).attr('r', 1.5)
          .attr('fill', '#475569');
        svg.append('text')
          .attr('x', g.x).attr('y', 78).attr('text-anchor', 'middle')
          .attr('fill', '#64748b').attr('font-size', 7).text(g.code);
      });

      // 停车场（从 API 数据加载，与 airport_display.json 同步）
      (data.parking_areas || []).forEach(p => {
        const pg = svg.append('g');
        pg.append('circle')
          .attr('cx', p.x).attr('cy', p.y).attr('r', 6)
          .attr('fill', '#1e293b').attr('stroke', '#475569').attr('stroke-width', 0.5);
        pg.append('text')
          .attr('x', p.x).attr('y', p.y + 2).attr('text-anchor', 'middle')
          .attr('fill', '#64748b').attr('font-size', 6)
          .text('P');
        pg.append('text')
          .attr('x', p.x).attr('y', p.y + 14).attr('text-anchor', 'middle')
          .attr('fill', '#4d5768').attr('font-size', 6)
          .text(p.code);
      });

      // 塔台（A区B区之间居中）
      const aGates = data.gates.filter(g => g.region === 'A');
      const bGates = data.gates.filter(g => g.region === 'B');
      const maxAX = aGates.length ? Math.max(...aGates.map(g => g.x)) : 300;
      const minBX = bGates.length ? Math.min(...bGates.map(g => g.x)) : 600;
      const towerX = (maxAX + minBX) / 2;
      svg.append('g')
        .attr('transform', `translate(${towerX}, 6) scale(0.024)`)
        .append('path')
        .attr('d', 'M590.512 735.456h-160v288h-64V724.848a31.936 31.936 0 0 1-6.832-12.192l-21.968-73.2H291.2a32 32 0 0 1-29.168-18.864l-115.2-256A32 32 0 0 1 176 319.472h130.928l171.584-142.992V101.968a56 56 0 1 1 64 0v74.512l171.584 142.976h130.928a32 32 0 0 1 29.184 45.136l-115.2 256a32 32 0 0 1-29.184 18.88h-46.512l-21.952 73.184c-1.392 4.64-3.76 8.752-6.848 12.192v298.608h-64v-288z m68.992-160h49.632l86.4-192H225.504l86.4 192H659.504z m-252.608-256h207.232l-103.616-86.336-103.616 86.336z m7.232 352h192.768l9.6-32H404.528l9.6 32z')
        .attr('fill', '#437ACF');
      svg.append('text')
        .attr('x', towerX).attr('y', 55).attr('text-anchor', 'middle')
        .attr('fill', '#64748b').attr('font-size', 8)
        .text('塔台');

      // 航班
      const flights = flightLayer.selectAll('.flight-group')
        .data(data.flights.filter(f => f.position), d => d.id);

      const fEnter = flights.enter().append('g')
        .attr('class', 'flight-group')
        .attr('transform', d => `translate(${d.position.x},${d.position.y})`);

      // 飞机 SVG 图标
      fEnter.append('g')
        .attr('transform', 'translate(0, -4) scale(0.024) translate(-512, -512)')
        .append('path')
        .attr('d', 'M995.679767 658.818049c-8.943231-1.490539-23.848617-2.981077-44.716157-4.471615-73.03639-8.943231-207.184862-26.829694-295.126638-38.754003l-19.377001-5.962154h-2.981077l-44.716157-13.414848c-4.471616 90.922853-10.43377 166.94032-17.886463 225.071325v10.43377l22.358078 10.43377 70.055313 32.791849c2.981077 1.490539 4.471616 4.471616 4.471616 7.452693l1.490539 55.149927v4.471615c0 2.981077-1.490539 5.962154-4.471616 4.471616l-114.77147-19.377001c-8.943231 22.358079-17.886463 34.282387-31.30131 35.772925h-1.490539c-13.414847 0-23.848617-11.924309-31.30131-35.772925l-114.77147 17.886463c-2.981077 0-4.471616-1.490539-4.471616-4.471616v-4.471616l1.490539-55.149927c0-2.981077 1.490539-5.962154 4.471615-7.452693l70.055313-32.791849 22.358079-10.43377V819.796215c-5.962154-58.131004-10.43377-134.148472-14.905386-225.071324l-46.206696 13.414847h-4.471615l-19.377002 4.471616c-87.941776 10.43377-222.090247 26.829694-295.126637 35.772925-20.86754 2.981077-35.772926 4.471616-44.716158 4.471616-23.848617 2.981077-25.339156-26.829694-7.452692-37.263464 2.981077-1.490539 56.640466-29.810771 123.714701-67.074236v-38.754003c0-14.905386 11.924309-26.829694 26.829695-26.829694s26.829694 11.924309 26.829694 26.829694v8.943232c40.244541-20.86754 81.979622-43.225619 119.243086-64.093159v-44.716157c0-14.905386 11.924309-26.829694 26.829694-26.829695s26.829694 11.924309 26.829694 26.829695v14.905385c23.848617-11.924309 43.225619-23.848617 56.640466-31.30131-1.490539-174.393013 11.924309-308.541485 61.112082-332.390101 2.981077-1.490539 4.471616-1.490539 7.452693-2.981078 1.490539 0 4.471616 0 5.962154-1.490538h5.962154c1.490539 0 4.471616 0 5.962154 1.490538 2.981077 0 4.471616 1.490539 7.452693 2.981078 49.187773 23.848617 62.60262 157.997089 58.131005 332.390101 13.414847 7.452693 32.791849 17.886463 55.149927 29.810772v-14.905386c0-14.905386 11.924309-26.829694 26.829694-26.829694s26.829694 11.924309 26.829695 26.829694v44.716157c37.263464 20.86754 78.998544 43.225619 119.243085 65.583698V506.783115c0-14.905386 11.924309-26.829694 26.829695-26.829694s26.829694 11.924309 26.829694 26.829694v44.716157c68.564774 37.263464 122.224163 67.074236 123.714702 68.564775 25.339156 10.43377 23.848617 41.73508-1.490539 38.754002z')
        .attr('fill', d => STATUS_COLORS.FLIGHT[d.status] || '#94a3b8');
      // 航班号
      fEnter.append('text')
        .attr('x', 0).attr('y', 18).attr('text-anchor', 'middle')
        .attr('fill', 'var(--map-text, #e2e8f0)').attr('font-size', 8).attr('font-weight', 'bold')
        .text(d => d.flight_no);
      // 机型
      fEnter.append('text')
        .attr('x', 0).attr('y', 30).attr('text-anchor', 'middle')
        .attr('fill', '#64748b').attr('font-size', 7)
        .text(d => d.aircraft_type || '');
      // 全部任务完成后显示"待起飞"标签
      fEnter.append('text')
        .attr('x', 0).attr('y', 41).attr('text-anchor', 'middle')
        .attr('font-size', 6.5).attr('font-weight', '600')
        .attr('fill', '#22c55e')
        .text(d => {
          var done = d.task_done || 0;
          var total = d.task_total || 0;
          if (done > 0 && done === total) return '待起飞';
          return '';
        });
      // 服务车辆药丸标签
      var vColors = {'TOW': '#a855f7', 'GPU': '#f59e0b', 'STAIR': '#3b82f6', 'BUS': '#10b981', 'FUEL': '#eab308', 'BAG': '#22c55e', 'CLEAN': '#ef4444'};
      fEnter.each(function(d) {
        var group = d3.select(this);
        (d.assigned_vehicles || []).forEach(function(v, i) {
          var vy = 46 + i * 17;
          var label = v.type_icon + ' ' + v.plate;
          var pw = Math.max(label.length * 3.8 + 14, 46);
          var c = vColors[v.type] || '#64748b';
          var pill = group.append('g');
          pill.append('rect')
            .attr('x', -pw / 2).attr('y', vy - 7).attr('width', pw).attr('height', 15)
            .attr('rx', 7.5).attr('fill', c + '18').attr('stroke', c + '30').attr('stroke-width', 0.5);
          pill.append('text')
            .attr('x', 0).attr('y', vy + 3).attr('text-anchor', 'middle')
            .attr('fill', '#c8d0da').attr('font-size', 6).attr('font-weight', '500')
            .text(label);
        });
      });

      flights.select('path').attr('fill', d => STATUS_COLORS.FLIGHT[d.status] || '#94a3b8');
      flights.exit().remove();
    })
    .catch(err => {
      svg.append('text')
        .attr('x', MAP_W / 2).attr('y', MAP_H / 2).attr('text-anchor', 'middle')
        .attr('fill', '#ef4444').attr('font-size', 16).text('Data load failed');
      console.error('Map data error:', err);
    });
}

/**
 * 航班起飞弹窗 — CS:GO 风格居中卡片
 * @param {Object|null} flight — 航班数据 {id, flight_no, airline, gate, aircraft_type, status}
 */
function showDeparturePopup(flight) {
  var flightNo = (flight && flight.flight_no) || null;
  var airline = (flight && flight.airline) || null;
  var gateCode = (flight && flight.gate) || null;

  // 构建 DOM
  var backdrop = document.createElement('div');
  backdrop.className = 'departure-popup-backdrop';

  var card = document.createElement('div');
  card.className = 'departure-popup-card';

  // 飞机图标
  var icon = document.createElement('span');
  icon.className = 'departure-popup-icon';
  icon.textContent = '🛫';

  // 标题
  var title = document.createElement('div');
  title.className = 'departure-popup-title';
  title.textContent = '航班已正常起飞';

  // 航班号
  var flightEl = document.createElement('div');
  flightEl.className = 'departure-popup-flight';
  flightEl.textContent = flightNo || '---';

  // 辅助信息行
  var info = document.createElement('div');
  info.className = 'departure-popup-info';

  if (airline) {
    var airlineSpan = document.createElement('span');
    airlineSpan.textContent = airline;
    info.appendChild(airlineSpan);
  }

  if (gateCode) {
    if (airline) {
      var sep1 = document.createElement('span');
      sep1.className = 'sep';
      sep1.textContent = '·';
      info.appendChild(sep1);
    }
    var gateTag = document.createElement('span');
    gateTag.className = 'gate-tag';
    gateTag.textContent = gateCode + ' 登机口';
    info.appendChild(gateTag);
  }

  // 进度条
  var progressTrack = document.createElement('div');
  progressTrack.className = 'departure-popup-progress-track';
  var progressBar = document.createElement('div');
  progressBar.className = 'departure-popup-progress-bar';
  progressTrack.appendChild(progressBar);

  // 组装
  card.appendChild(icon);
  card.appendChild(title);
  card.appendChild(flightEl);
  card.appendChild(info);
  card.appendChild(progressTrack);
  backdrop.appendChild(card);
  document.body.appendChild(backdrop);

  // 点击任意位置提前关闭
  backdrop.addEventListener('click', function() {
    dismissPopup(backdrop, card);
  });

  // 自动移除（4 秒，等进度条跑完）
  var autoTimer = setTimeout(function() {
    dismissPopup(backdrop, card);
  }, 6000);

  // 将 timer 存到元素上，点击提前关闭时可以取消
  backdrop._autoTimer = autoTimer;

  function dismissPopup(bd, cd) {
    if (bd._dismissed) return;
    bd._dismissed = true;
    if (bd._autoTimer) clearTimeout(bd._autoTimer);
    cd.classList.add('removing');
    bd.classList.add('removing');
    setTimeout(function() {
      bd.remove();
    }, 400);
  }
}
