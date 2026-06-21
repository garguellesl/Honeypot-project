const REFRESH_MS = 8000;
let timelineChart = null;
let lastSeenId = 0;

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

function fmtTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString();
}

function renderStats(stats) {
  document.getElementById('stat-total').textContent = stats.total;
  document.getElementById('stat-ips').textContent = stats.unique_ips;

  const dominant = stats.by_protocol.sort((a, b) => b.c - a.c)[0];
  document.getElementById('stat-protocol').textContent = dominant ? dominant.protocol.toUpperCase() : '—';

  document.getElementById('stat-last').textContent = stats.timeline.length
    ? stats.timeline[stats.timeline.length - 1].hour.replace('T', ' ') + 'h'
    : '—';
}

function renderCredentials(rows) {
  const body = document.getElementById('credentials-body');
  body.innerHTML = rows.map(r => `
    <tr>
      <td>${r.username || '(vacío)'}</td>
      <td>${r.password || '(vacío)'}</td>
      <td>${r.c}</td>
    </tr>`).join('');
}

function renderIps(rows) {
  const body = document.getElementById('ips-body');
  body.innerHTML = rows.map(r => `
    <tr>
      <td>${r.src_ip}</td>
      <td>${r.country || 'Unknown'}</td>
      <td>${r.c}</td>
    </tr>`).join('');
}

function renderTimeline(rows) {
  const labels = rows.map(r => r.hour.slice(11) + 'h');
  const data = rows.map(r => r.c);

  if (!timelineChart) {
    const ctx = document.getElementById('timeline-chart').getContext('2d');
    timelineChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Intentos',
          data,
          backgroundColor: 'rgba(232, 163, 61, 0.55)',
          borderRadius: 3,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#8A93A6' }, grid: { color: 'rgba(31,44,69,0.6)' } },
          y: { ticks: { color: '#8A93A6' }, grid: { color: 'rgba(31,44,69,0.6)' }, beginAtZero: true },
        },
      },
    });
  } else {
    timelineChart.data.labels = labels;
    timelineChart.data.datasets[0].data = data;
    timelineChart.update();
  }
}

function spawnRadarPing() {
  const svgns = 'http://www.w3.org/2000/svg';
  const group = document.getElementById('radar-pings');
  const angle = Math.random() * 2 * Math.PI;
  const radius = 20 + Math.random() * 70;
  const cx = 100 + radius * Math.cos(angle);
  const cy = 100 + radius * Math.sin(angle);

  const circle = document.createElementNS(svgns, 'circle');
  circle.setAttribute('cx', cx);
  circle.setAttribute('cy', cy);
  circle.setAttribute('r', 4);
  circle.setAttribute('class', 'radar-ping');
  group.appendChild(circle);
  setTimeout(() => circle.remove(), 3000);
}

function renderTerminal(attempts) {
  const term = document.getElementById('terminal');
  const newOnes = attempts.filter(a => a.id > lastSeenId).reverse();

  newOnes.forEach(a => {
    const line = document.createElement('div');
    line.className = 'terminal-line';
    line.innerHTML = `<span class="ts">${fmtTime(a.timestamp)}</span> ` +
      `<span class="proto">${a.protocol}</span> ` +
      `<span class="ip">${a.src_ip}</span> ` +
      `user="${a.username}" pass="${a.password}" (${a.country})`;
    term.appendChild(line);
    spawnRadarPing();
  });

  if (attempts.length) {
    lastSeenId = Math.max(...attempts.map(a => a.id));
  }

  // Mantiene el scroll abajo y limita el histórico visible
  while (term.children.length > 200) term.removeChild(term.firstChild);
  term.scrollTop = term.scrollHeight;
}

async function refresh() {
  try {
    const [stats, attempts] = await Promise.all([
      fetchJSON('/api/stats'),
      fetchJSON('/api/attempts'),
    ]);
    renderStats(stats);
    renderCredentials(stats.top_credentials);
    renderIps(stats.top_ips);
    renderTimeline(stats.timeline);
    renderTerminal(attempts);
    document.getElementById('status-text').textContent = 'en escucha';
  } catch (e) {
    document.getElementById('status-text').textContent = 'sin conexión';
    console.error(e);
  }
}

refresh();
setInterval(refresh, REFRESH_MS);
