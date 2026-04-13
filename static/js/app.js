/* Main application entry point: refresh loop and initialization. */

async function refresh() {
    try {
        const resp = await fetch('/api/leaderboard');
        const data = await resp.json();
        renderSeasonProgress(data.season_start, data.season_end);
        renderVersus(data);
        renderWeekly(data);
        renderHeatmaps(data.distance_timeline, data.season_start, data.season_end);
        renderDistanceChart(data.distance_timeline);
        renderRecent(data.recent_rides, data.leaderboard);
    } catch (err) {
        console.error('Failed to refresh:', err);
    }
}

refresh();
setInterval(refresh, 60000);
