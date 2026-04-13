/* Dedicated "This Week" section with per-rider weekly stats. */

function renderWeekly(data) {
    const section = document.getElementById('weeklySection');
    const riders = data.leaderboard;
    if (!riders || riders.length < 2) {
        section.innerHTML = '';
        return;
    }

    ensureColorMap(riders);
    const [left, right] = sortedByColor(riders);
    const cL = riderColor(left), cR = riderColor(right);

    const weekRange = data.week_start && data.week_end
        ? `${formatDate(data.week_start)} – ${formatDate(data.week_end)}` : '';

    const totalWeekKm = (left.week_km || 0) + (right.week_km || 0);
    const leftPct = totalWeekKm > 0 ? ((left.week_km || 0) / totalWeekKm * 100) : 50;
    const rightPct = 100 - leftPct;
    const weekGap = Math.abs((left.week_km || 0) - (right.week_km || 0));

    section.innerHTML = `
    <h2 class="section-title">${icon('calendar')} This Week</h2>
    ${weekRange ? `<p class="weekly-range">${weekRange}</p>` : ''}
    <div class="weekly-card">
        <div class="weekly-tug">
            <div class="tug-fill left" style="width:${leftPct}%"></div>
            <div class="tug-fill right" style="width:${rightPct}%"></div>
            <div class="tug-gap">${weekGap > 0 ? '+' + formatKm(weekGap) + ' km' : 'Tied!'}</div>
        </div>
        <div class="weekly-stats">
            ${statRow(left.week_km, right.week_km, 'Distance', 'km', 'route', 0, cL, cR)}
            ${statRow(left.week_ride_count, right.week_ride_count, 'Rides', '', 'bike', 1, cL, cR)}
            ${statRow(left.week_longest_km, right.week_longest_km, 'Longest Ride', 'km', 'ruler', 2, cL, cR)}
            ${statRow(left.week_avg_kmh, right.week_avg_kmh, 'Avg Speed', 'km/h', 'speed', 3, cL, cR)}
        </div>
    </div>`;
}
