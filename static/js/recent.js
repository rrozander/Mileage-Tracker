/* Two-column recent rides, one column per rider. */

function renderRecent(rides, leaderboard) {
    const container = document.getElementById('recentRides');
    if (!rides || rides.length === 0 || !leaderboard || leaderboard.length < 2) {
        container.innerHTML = '<p class="empty">No rides yet this season.</p>';
        return;
    }

    ensureColorMap(leaderboard);
    const ordered = sortedByColor(leaderboard);

    const cols = ordered.map(rider => {
        const color = riderColor(rider);
        const myRides = rides.filter(r => r.athlete_name === rider.name);
        const avatar = rider.avatar_url
            ? `<img src="${rider.avatar_url}" alt="${rider.name}" class="col-avatar">`
            : `<div class="col-avatar placeholder">${rider.name.charAt(0)}</div>`;

        let cards = '';
        if (myRides.length === 0) {
            cards = '<div class="rides-empty">No recent rides</div>';
        } else {
            cards = myRides.map(r => `
                <div class="ride-card">
                    <div class="ride-card-top">
                        <span class="ride-card-name">${r.ride_name || 'Ride'}</span>
                        <span class="ride-card-km" style="--rider-color:${color}">${formatKm(r.distance_km)} km</span>
                    </div>
                    <div class="ride-card-bottom">
                        ${r.avg_kmh != null ? `<span>${formatKm(r.avg_kmh)} km/h</span>` : ''}
                        <span>${formatDate(r.ride_date)}</span>
                    </div>
                </div>`).join('');
        }

        return `<div class="rides-column" style="--rider-color:${color}">
            <div class="rides-column-header" style="--rider-color:${color}">
                ${avatar} ${rider.name}
            </div>
            ${cards}
        </div>`;
    });

    container.innerHTML = cols.join('');
}
