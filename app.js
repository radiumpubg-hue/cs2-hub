// CS2 Hub — app.js
// Загружает JSON-данные и рендерит интерфейс

const DATA_BASE = './data/';

let state = {
  rankings: [],
  tournaments: [],
  vrsPoints: {},
  activeRegion: 'all',
};

// ─── INIT ───────────────────────────────────────────────
async function init() {
  setupTabs();
  await loadAll();
}

async function loadAll() {
  try {
    const [rankings, tournaments, vrsPoints] = await Promise.all([
      fetch(DATA_BASE + 'rankings.json').then(r => r.json()),
      fetch(DATA_BASE + 'tournaments.json').then(r => r.json()),
      fetch(DATA_BASE + 'vrs_points.json').then(r => r.json()),
    ]);

    state.rankings = rankings.teams || [];
    state.tournaments = tournaments.tournaments || [];
    state.vrsPoints = vrsPoints.tournaments || {};

    const updated = rankings.last_updated || '';
    if (updated) {
      const d = new Date(updated);
      document.getElementById('last-updated').textContent =
        'Обновлено: ' + d.toLocaleString('ru-RU', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' });
    }

    renderRankings();
    renderTournaments();
    populateCalcSelect();
    setupRegionFilters();
    setupCalcSelect();

  } catch (e) {
    console.error('Ошибка загрузки данных:', e);
    document.getElementById('rankings-body').innerHTML =
      '<tr><td colspan="5" class="loading-row">⚠ Данные недоступны. Проверь, что файлы data/*.json существуют.</td></tr>';
  }
}

// ─── TABS ────────────────────────────────────────────────
function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });
}

// ─── RANKINGS ────────────────────────────────────────────
function renderRankings(region = 'all') {
  const tbody = document.getElementById('rankings-body');
  let teams = state.rankings;

  if (region !== 'all') {
    teams = teams.filter(t => (t.region || '').toLowerCase() === region);
  }

  if (!teams.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="loading-row">Нет данных</td></tr>';
    return;
  }

  tbody.innerHTML = teams.map((team, i) => {
    const rank = region === 'all' ? team.global_rank || (i + 1) : (i + 1);
    const rankClass = rank <= 3 ? 'rank-top' : '';
    const regionKey = (team.region || '').toLowerCase();
    const regionLabel = { europe: 'Европа', americas: 'Америка', asia: 'Азия' }[regionKey] || team.region;
    const status = getStatus(team, regionKey);

    return `<tr>
      <td class="${rankClass}">${rank}</td>
      <td>
        <span class="team-flag">${team.flag || '🏳'}</span>
        <span class="team-name">${team.name}</span>
      </td>
      <td><span class="region-badge region-${regionKey}">${regionLabel}</span></td>
      <td class="vrs-points">${(team.points || 0).toLocaleString()}</td>
      <td style="text-align:center"><span class="status-badge status-${status.cls}">${status.label}</span></td>
    </tr>`;
  }).join('');
}

function getStatus(team, region) {
  const pts = team.points || 0;
  // Упрощённая логика: топ-8 по региону = квал, 9-16 = претендент, остальные = нет
  if (team.qualified) return { cls: 'qualified', label: 'Квалифицирован' };
  if (pts > 1000)     return { cls: 'qualified', label: 'Квалифицирован' };
  if (pts > 400)      return { cls: 'contender', label: 'Претендент' };
  return { cls: 'eliminated', label: 'Не квалифицирован' };
}

function setupRegionFilters() {
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeRegion = btn.dataset.region;
      renderRankings(state.activeRegion);
    });
  });
}

// ─── TOURNAMENTS ─────────────────────────────────────────
function renderTournaments() {
  const grid = document.getElementById('tournaments-grid');

  if (!state.tournaments.length) {
    grid.innerHTML = '<div class="loading-card">Нет данных о турнирах</div>';
    return;
  }

  grid.innerHTML = state.tournaments.map(t => {
    const regionKey = (t.region || 'europe').toLowerCase();
    const regionLabel = { europe: 'Европа', americas: 'Америка', asia: 'Азия', global: 'Глобальный' }[regionKey] || t.region;
    const slotsHtml = buildSlotsHtml(t);

    return `<div class="tournament-card">
      <div class="card-header">
        <div class="card-title">${t.name}</div>
        <span class="region-badge region-${regionKey === 'global' ? 'europe' : regionKey}">${regionLabel}</span>
      </div>
      <div class="card-meta">
        <div class="meta-item">
          <span class="meta-label">Дата</span>
          <span class="meta-value">${t.date || 'TBD'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Слоты на Мейджор</span>
          <span class="meta-value">${t.major_slots || '?'}</span>
        </div>
        <div class="meta-item">
          <span class="meta-label">Статус</span>
          <span class="meta-value">${t.status || 'Upcoming'}</span>
        </div>
      </div>
      <div class="card-slots">
        <div class="slots-label">Шансы квалификации (топ команды)</div>
        ${slotsHtml}
      </div>
    </div>`;
  }).join('');
}

function buildSlotsHtml(tournament) {
  const region = (tournament.region || '').toLowerCase();
  let teams = state.rankings.filter(t =>
    region === 'global' ? true : (t.region || '').toLowerCase() === region
  );
  teams = teams.slice(0, 8);

  const slots = tournament.major_slots || 8;

  return teams.map((team, i) => {
    const chance = calcChance(i, slots, teams.length);
    const chanceClass = chance >= 70 ? 'chance-high' : chance >= 35 ? 'chance-medium' : 'chance-low';
    return `<div class="slot-item">
      <div class="slot-team">
        <span class="slot-rank">#${i + 1}</span>
        <span>${team.flag || '🏳'} ${team.name}</span>
      </div>
      <span class="slot-chance ${chanceClass}">${chance}%</span>
    </div>`;
  }).join('');
}

function calcChance(rank, slots, total) {
  // Простая модель: топ N команд имеют высокие шансы, далее убывает
  if (rank < slots) return Math.max(90 - rank * 5, 55);
  const overflow = rank - slots + 1;
  return Math.max(Math.round(50 - overflow * 9), 5);
}

// ─── CALCULATOR ──────────────────────────────────────────
function populateCalcSelect() {
  const sel = document.getElementById('calc-tournament');
  const keys = Object.keys(state.vrsPoints);
  keys.forEach(key => {
    const t = state.vrsPoints[key];
    const opt = document.createElement('option');
    opt.value = key;
    opt.textContent = t.name || key;
    sel.appendChild(opt);
  });
}

function setupCalcSelect() {
  document.getElementById('calc-tournament').addEventListener('change', e => {
    renderCalc(e.target.value);
  });
}

function renderCalc(tournamentKey) {
  const container = document.getElementById('calc-results');
  if (!tournamentKey) {
    container.innerHTML = '<div class="calc-placeholder">Выбери турнир выше</div>';
    return;
  }

  const t = state.vrsPoints[tournamentKey];
  if (!t || !t.placements) {
    container.innerHTML = '<div class="calc-placeholder">Нет данных для этого турнира</div>';
    return;
  }

  const rows = t.placements.map((p, i) => {
    let placeClass = '';
    if (i === 0) placeClass = 'points-gold';
    else if (i === 1) placeClass = 'points-silver';
    else if (i === 2) placeClass = 'points-bronze';

    return `<tr>
      <td class="points-row-place ${placeClass}">${p.place}</td>
      <td class="points-value">${p.vrs_points.toLocaleString()}</td>
      <td class="points-change">${p.description || ''}</td>
    </tr>`;
  }).join('');

  container.innerHTML = `
    <table class="points-table">
      <thead>
        <tr>
          <th>Место</th>
          <th>VRS Очки</th>
          <th>Примечание</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ─── START ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
