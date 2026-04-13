/* Cumulative distance Chart.js line chart with gradient fills and a
   dashed "Today" vertical marker. */

const todayLinePlugin = {
    id: 'todayLine',
    afterDraw(chart) {
        const todayStr = new Date().toISOString().slice(0, 10);
        const xAxis = chart.scales.x;
        const x = xAxis.getPixelForValue(todayStr);
        if (x < xAxis.left || x > xAxis.right) return;
        const { ctx, chartArea: { top, bottom } } = chart;
        const muted = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-muted').trim() || '#94a3b8';
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = muted;
        ctx.lineWidth = 1;
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = muted;
        ctx.font = '10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Today', x, top - 5);
        ctx.restore();
    }
};

function buildPerRideDatasets(timeline) {
    const byRider = {};
    timeline.forEach(({ athlete_name, ride_date, distance_km, ride_name }) => {
        if (!byRider[athlete_name]) byRider[athlete_name] = [];
        byRider[athlete_name].push({ date: ride_date, km: distance_km, rideName: ride_name || 'Ride' });
    });

    const canvas = document.getElementById('distanceChart');
    const ctx2d = canvas.getContext('2d');

    return Object.entries(byRider).map(([name, rides]) => {
        let cumulative = 0;
        const points = rides.map(r => {
            cumulative += r.km;
            return { x: r.date, y: Math.round(cumulative * 10) / 10, rideKm: Math.round(r.km * 10) / 10, rideName: r.rideName };
        });
        const color = (colorMap && colorMap[name]) || RIDER_COLORS[0];
        const gradient = ctx2d.createLinearGradient(0, 0, 0, canvas.clientHeight || 300);
        gradient.addColorStop(0, color + '35');
        gradient.addColorStop(1, color + '05');
        return {
            label: name,
            data: points,
            borderColor: color,
            backgroundColor: gradient,
            fill: true,
            tension: 0.3,
            pointRadius: 4,
            pointHoverRadius: 7,
            borderWidth: 2.5,
        };
    });
}

function renderDistanceChart(timeline) {
    const canvas = document.getElementById('distanceChart');
    if (!timeline || timeline.length === 0) return;
    const datasets = buildPerRideDatasets(timeline);
    const tc = getThemeColors();

    if (distanceChartInstance) {
        distanceChartInstance.data.datasets = datasets;
        distanceChartInstance.options.scales.x.ticks.color = tc.muted;
        distanceChartInstance.options.scales.y.ticks.color = tc.muted;
        distanceChartInstance.options.scales.y.grid.color = tc.border + '55';
        distanceChartInstance.options.plugins.legend.labels.color = tc.text;
        distanceChartInstance.update();
        return;
    }

    distanceChartInstance = new Chart(canvas, {
        type: 'line',
        data: { datasets },
        plugins: [todayLinePlugin],
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'nearest', intersect: true },
            plugins: {
                legend: { labels: { color: tc.text, boxWidth: 14, font: { family: 'Inter' } } },
                tooltip: {
                    callbacks: {
                        label: (item) => {
                            const pt = item.dataset.data[item.dataIndex];
                            return `${item.dataset.label}: ${pt.rideKm} km ride (${pt.y} km total) \u2014 ${pt.rideName}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: { unit: 'week', tooltipFormat: 'MMM d' },
                    ticks: { color: tc.muted, font: { family: 'Inter' } },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: tc.muted, callback: v => v + ' km', font: { family: 'Inter' } },
                    grid: { color: tc.border + '55' },
                }
            }
        }
    });
}

function updateChartTheme() {
    if (!distanceChartInstance) return;
    const tc = getThemeColors();
    distanceChartInstance.options.scales.x.ticks.color = tc.muted;
    distanceChartInstance.options.scales.y.ticks.color = tc.muted;
    distanceChartInstance.options.scales.y.grid.color = tc.border + '55';
    distanceChartInstance.options.plugins.legend.labels.color = tc.text;
    distanceChartInstance.update();
}
