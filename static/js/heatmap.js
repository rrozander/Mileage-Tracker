/* Side-by-side GitHub-style ride activity heatmaps. */

function renderHeatmaps(timeline, seasonStart, seasonEnd) {
    const container = document.getElementById('heatmapSection');
    if (!timeline || timeline.length === 0) { container.innerHTML = ''; return; }

    const byAthlete = {};
    timeline.forEach(r => {
        if (!byAthlete[r.athlete_name]) byAthlete[r.athlete_name] = {};
        byAthlete[r.athlete_name][r.ride_date] =
            (byAthlete[r.athlete_name][r.ride_date] || 0) + r.distance_km;
    });

    const athletes = Object.keys(byAthlete).sort((a, b) => {
        const ca = colorMap ? (colorMap[a] || '') : '';
        const cb = colorMap ? (colorMap[b] || '') : '';
        return ca < cb ? -1 : ca > cb ? 1 : 0;
    });

    const start = new Date(seasonStart + 'T00:00:00');
    const end = new Date(seasonEnd + 'T00:00:00');
    const now = new Date();
    const latestRide = timeline.reduce((max, r) => r.ride_date > max ? r.ride_date : max, '');
    const latestData = latestRide ? new Date(latestRide + 'T00:00:00') : now;
    const endDate = new Date(Math.min(end.getTime(), Math.max(now.getTime(), latestData.getTime())));

    let maxKm = 0;
    Object.values(byAthlete).forEach(dates =>
        Object.values(dates).forEach(km => { if (km > maxKm) maxKm = km; })
    );
    if (maxKm === 0) maxKm = 1;

    const cellSize = 10, cellGap = 2, pitch = cellSize + cellGap;

    let html = `<h2 class="section-title">${icon('calendar')} Ride Activity</h2><div class="heatmaps">`;

    athletes.forEach((name) => {
        const data = byAthlete[name] || {};
        const color = (colorMap && colorMap[name]) || RIDER_COLORS[0];

        const startDow = (start.getDay() + 6) % 7;
        const mondayOfStart = new Date(start);
        mondayOfStart.setDate(start.getDate() - startDow);

        let cells = '';
        const d = new Date(start);
        while (d <= endDate) {
            const dateStr = d.toISOString().slice(0, 10);
            const dow = (d.getDay() + 6) % 7;
            const daysSinceMon = Math.floor((d - mondayOfStart) / 86400000);
            const col = Math.floor(daysSinceMon / 7);
            const km = data[dateStr] || 0;
            const opacity = km > 0 ? (0.25 + (km / maxKm) * 0.75).toFixed(2) : '0.08';
            const tip = km > 0 ? formatKm(km) + ' km' : 'Rest day';
            cells += `<rect x="${col * pitch}" y="${dow * pitch}" width="${cellSize}" height="${cellSize}" rx="2" fill="${color}" opacity="${opacity}" data-tip="${tip}"></rect>`;
            d.setDate(d.getDate() + 1);
        }

        const totalDays = Math.floor((endDate - mondayOfStart) / 86400000);
        const totalWeeks = Math.floor(totalDays / 7) + 1;
        const svgW = totalWeeks * pitch;
        const gridH = 7 * pitch;
        const labelY = gridH + 12;
        const svgH = gridH + 18;

        let monthLabels = '';
        const placed = {};
        const m = new Date(start);
        while (m <= endDate) {
            const first = new Date(m.getFullYear(), m.getMonth(), 1);
            if (first < start) first.setTime(start.getTime());
            const key = first.getFullYear() + '-' + first.getMonth();
            if (!placed[key]) {
                placed[key] = true;
                const col = Math.floor((first - mondayOfStart) / 86400000 / 7);
                monthLabels += `<text x="${col * pitch}" y="${labelY}" class="heatmap-month">${MONTH_NAMES[first.getMonth()]}</text>`;
            }
            m.setMonth(m.getMonth() + 1);
            m.setDate(1);
        }

        html += `<div class="heatmap" style="--rider-color:${color}">
            <h3>${name}</h3>
            <svg class="heatmap-grid" viewBox="0 0 ${svgW} ${svgH}" width="${svgW}" height="${svgH}">${cells}${monthLabels}</svg>
            <div class="heatmap-legend">
                <span>Less</span>
                ${[0.08, 0.3, 0.55, 0.8, 1.0].map(o => `<div class="heatmap-legend-cell" style="background:${color};opacity:${o}"></div>`).join('')}
                <span>More</span>
            </div>
        </div>`;
    });

    html += '</div>';
    container.innerHTML = html;
    _initHeatmapTooltip();
}

function _initHeatmapTooltip() {
    let tip = document.getElementById('heatmapTip');
    if (!tip) {
        tip = document.createElement('div');
        tip.id = 'heatmapTip';
        tip.className = 'heatmap-tip';
        document.body.appendChild(tip);
    }

    const section = document.getElementById('heatmapSection');
    section.addEventListener('mouseover', function (e) {
        const rect = e.target.closest('rect[data-tip]');
        if (!rect) return;
        tip.textContent = rect.getAttribute('data-tip');
        tip.classList.add('visible');
    });

    section.addEventListener('mousemove', function (e) {
        if (!tip.classList.contains('visible')) return;
        const pad = 12;
        let x = e.clientX + pad;
        let y = e.clientY + pad;
        const tw = tip.offsetWidth;
        const th = tip.offsetHeight;
        if (x + tw > window.innerWidth - pad) x = e.clientX - tw - pad;
        if (y + th > window.innerHeight - pad) y = e.clientY - th - pad;
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
    });

    section.addEventListener('mouseout', function (e) {
        const rect = e.target.closest('rect[data-tip]');
        if (!rect) return;
        tip.classList.remove('visible');
    });
}
