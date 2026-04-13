/* VS head-to-head layout: panels, tug-of-war, stat rows, sparklines,
   count-up animation, and celebration confetti. */

/* ---- Season progress ---- */

function renderSeasonProgress(seasonStart, seasonEnd) {
    const el = document.getElementById('seasonProgress');
    const start = new Date(seasonStart + 'T00:00:00');
    const end = new Date(seasonEnd + 'T00:00:00');
    const now = new Date();
    if (now < start) { el.innerHTML = ''; return; }
    const total = end - start;
    const elapsed = Math.min(now - start, total);
    const pct = Math.max(0, Math.min(100, (elapsed / total) * 100));
    const daysLeft = Math.max(0, Math.ceil((end - now) / 86400000));
    el.innerHTML = `
        <div class="season-bar">
            <div class="season-fill" style="width:${pct}%"></div>
            <div class="season-marker" style="left:${pct}%"></div>
        </div>
        <div class="season-meta">
            <span>${Math.round(pct)}% complete</span>
            <span>${daysLeft > 0 ? daysLeft + ' days remaining' : 'Season ended'}</span>
        </div>`;
}

/* ---- Weekly mini bar chart ---- */

function buildSparkline(timeline, athleteName, color) {
    const rides = timeline.filter(r => r.athlete_name === athleteName);
    if (rides.length === 0) return '';

    const weeklyKm = {};
    rides.forEach(r => {
        const d = new Date(r.ride_date + 'T00:00:00');
        const mon = new Date(d);
        mon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
        const key = mon.toISOString().slice(0, 10);
        weeklyKm[key] = (weeklyKm[key] || 0) + r.distance_km;
    });

    const weeks = Object.keys(weeklyKm).sort();
    const vals = weeks.map(w => Math.round(weeklyKm[w] * 10) / 10);
    if (vals.length === 0) return '';

    const maxV = Math.max(...vals, 1);
    const maxWeekIdx = vals.indexOf(Math.max(...vals));
    const w = 180, h = 44, topPad = 14, botPad = 4, sidePad = 4;
    const barArea = h - topPad - botPad;
    const gap = 3;
    const barW = Math.min(16, Math.max(4, (w - sidePad * 2 - gap * (vals.length - 1)) / vals.length));
    const totalW = vals.length * barW + (vals.length - 1) * gap;
    const offsetX = (w - totalW) / 2;

    const nowKey = (() => {
        const d = new Date();
        const mon = new Date(d);
        mon.setDate(d.getDate() - ((d.getDay() + 6) % 7));
        return mon.toISOString().slice(0, 10);
    })();

    let bars = '';
    vals.forEach((v, i) => {
        const barH = Math.max(2, (v / maxV) * barArea);
        const x = offsetX + i * (barW + gap);
        const y = topPad + barArea - barH;
        const isCurrent = weeks[i] === nowKey;
        const opacity = isCurrent ? '1' : '0.65';
        const radius = Math.min(barW / 2, 3);
        bars += `<rect x="${x}" y="${y}" width="${barW}" height="${barH}" rx="${radius}" fill="${color}" opacity="${opacity}"/>`;
        if (i === maxWeekIdx) {
            bars += `<text x="${x + barW / 2}" y="${y - 3}" text-anchor="middle" fill="${color}" font-size="7" font-weight="600" font-family="Inter, sans-serif">${Math.round(v)}</text>`;
        }
    });

    return `<div class="mini-chart">
        <svg class="mini-chart-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMidYMid meet">
            ${bars}
        </svg>
        <span class="mini-chart-label">Weekly km</span>
    </div>`;
}

/* ---- Stat comparison row ---- */

function statRow(v1, v2, label, unit, iconName, idx, c1, c2) {
    const f = (v) => v != null && !Number.isNaN(Number(v)) ? formatKm(v) : '\u2014';
    const n1 = Number(v1) || 0, n2 = Number(v2) || 0;
    const suffix = unit ? ' ' + unit : '';
    const w1 = n1 > n2 ? 'winner' : '', w2 = n2 > n1 ? 'winner' : '';
    return `<div class="stat-row" style="--i:${idx}">
        <span class="stat-value left ${w1}" style="--rider-color:${c1}">${f(v1)}${v1 != null ? suffix : ''}</span>
        <span class="stat-label">${icon(iconName)} ${label}</span>
        <span class="stat-value right ${w2}" style="--rider-color:${c2}">${f(v2)}${v2 != null ? suffix : ''}</span>
    </div>`;
}

/* ---- VS layout render ---- */

function renderVersus(data) {
    const section = document.getElementById('versusSection');
    const riders = data.leaderboard;
    if (!riders || riders.length < 2) {
        section.innerHTML = '<p class="empty">Waiting for riders\u2026</p>';
        return;
    }

    ensureColorMap(riders);
    const [left, right] = sortedByColor(riders);
    const cL = riderColor(left), cR = riderColor(right);
    const glowL = cL + '30', glowR = cR + '30';

    const leaderL = left.total_km >= right.total_km && left.total_km > 0;
    const leaderR = right.total_km > left.total_km && right.total_km > 0;

    const total = left.total_km + right.total_km;
    const leftPct = total > 0 ? (left.total_km / total * 100) : 50;
    const rightPct = 100 - leftPct;
    const gap = Math.abs(left.total_km - right.total_km);

    const stravaL = `https://www.strava.com/athletes/${left.strava_id}`;
    const stravaR = `https://www.strava.com/athletes/${right.strava_id}`;

    section.innerHTML = `
    <div class="vs-container">
        <div class="vs-panel left ${leaderL ? 'leader' : ''}" style="--rider-color:${cL};--glow-color:${glowL}">
            ${avatarHtml(left)}
            <span class="rider-name">${left.name}</span>
            <a class="strava-link" href="${stravaL}" target="_blank" rel="noopener" style="--rider-color:${cL}">View Strava</a>
            <span class="rider-km" style="--rider-color:${cL}" data-countup="${left.total_km}" data-suffix=" km">0 km</span>
            <span class="rider-rides">${left.ride_count} ride${left.ride_count !== 1 ? 's' : ''}</span>
            ${buildSparkline(data.distance_timeline || [], left.name, cL)}
        </div>
        <div class="vs-divider">VS</div>
        <div class="vs-panel right ${leaderR ? 'leader' : ''}" style="--rider-color:${cR};--glow-color:${glowR}">
            ${avatarHtml(right)}
            <span class="rider-name">${right.name}</span>
            <a class="strava-link" href="${stravaR}" target="_blank" rel="noopener" style="--rider-color:${cR}">View Strava</a>
            <span class="rider-km" style="--rider-color:${cR}" data-countup="${right.total_km}" data-suffix=" km">0 km</span>
            <span class="rider-rides">${right.ride_count} ride${right.ride_count !== 1 ? 's' : ''}</span>
            ${buildSparkline(data.distance_timeline || [], right.name, cR)}
        </div>
    </div>
    <div class="tug-of-war">
        <div class="tug-fill left" style="width:${leftPct}%"></div>
        <div class="tug-fill right" style="width:${rightPct}%"></div>
        <div class="tug-gap">${gap > 0 ? '+' + formatKm(gap) + ' km' : 'Tied!'}</div>
    </div>
    <div class="stat-comparisons">
        ${statRow(left.total_km, right.total_km, 'Total Distance', 'km', 'route', 0, cL, cR)}
        ${statRow(left.ride_count, right.ride_count, 'Total Rides', '', 'bike', 1, cL, cR)}
        ${statRow(left.avg_ride_km, right.avg_ride_km, 'Avg Ride', 'km', 'ruler', 2, cL, cR)}
        ${statRow(left.overall_avg_kmh, right.overall_avg_kmh, 'Avg Speed', 'km/h', 'speed', 3, cL, cR)}
    </div>`;

    animateCountUps();
    checkCelebration(riders);
}

/* ---- Count-up animation ---- */

function animateCountUps() {
    document.querySelectorAll('[data-countup]').forEach(el => {
        const target = parseFloat(el.dataset.countup);
        const suffix = el.dataset.suffix || '';
        if (!target || target === 0) { el.textContent = '0' + suffix; return; }
        const duration = 1000;
        const start = performance.now();
        function tick(now) {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = formatKm(target * eased) + suffix;
            if (progress < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    });
}

/* ---- Celebration / confetti ---- */

function checkCelebration(riders) {
    if (riders.length < 2) return;
    const leaderId = riders[0].total_km >= riders[1].total_km ? riders[0].athlete_id : riders[1].athlete_id;
    if (prevLeaderId !== null && prevLeaderId !== leaderId) {
        const leaderPanel = document.querySelector('.vs-panel.leader');
        if (leaderPanel) spawnConfetti(leaderPanel);
    }
    prevLeaderId = leaderId;
}

function spawnConfetti(el) {
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height * 0.3;
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'confetti';
        p.style.left = cx + 'px';
        p.style.top = cy + 'px';
        p.style.setProperty('--dx', (Math.random() - 0.5) * 280 + 'px');
        p.style.setProperty('--dy', (-Math.random() * 180 - 40) + 'px');
        p.style.setProperty('--rot', (Math.random() * 720 - 360) + 'deg');
        p.style.setProperty('--delay', (Math.random() * 0.35) + 's');
        p.style.backgroundColor = CONFETTI_PALETTE[Math.floor(Math.random() * CONFETTI_PALETTE.length)];
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 1800);
    }
}
