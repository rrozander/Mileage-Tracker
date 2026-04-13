/* Shared constants, state, formatters, icons, and rider color logic. */

const RIDER_COLORS = ['#f97316', '#38bdf8'];
const CONFETTI_PALETTE = ['#f97316', '#38bdf8', '#facc15', '#4ade80', '#e879f9'];
const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

/* Mutable state shared across modules */
let colorMap = null;
let prevLeaderId = null;
let distanceChartInstance = null;

/* ---- Formatters ---- */

function formatKm(n) { return Number(n).toFixed(1); }

function formatOptional(n, suffix) {
    if (n == null || Number.isNaN(Number(n))) return '\u2014';
    return formatKm(n) + (suffix || '');
}

function formatDate(isoStr) {
    if (!isoStr) return isoStr;
    const p = isoStr.split('-');
    if (p.length !== 3) return isoStr;
    return `${MONTH_NAMES[parseInt(p[1],10)-1]} ${parseInt(p[2],10)}, ${p[0]}`;
}

/* ---- SVG Icons ---- */

function icon(name) {
    const paths = {
        route: '<path d="M3 17C6 7 9 17 12 10s5 7 5-3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
        bike: '<circle cx="5.5" cy="13.5" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="14.5" cy="13.5" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5.5 13.5l4-7h3l2 7M8 9.5h5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>',
        speed: '<circle cx="10" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 11l3-4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="10" cy="11" r="1" fill="currentColor"/>',
        calendar: '<rect x="3" y="4" width="14" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M3 8h14M7 2v4M13 2v4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
        ruler: '<path d="M4 16L16 4M7 16v-3M10 16v-5M13 16v-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
        trophy: '<path d="M6 2h8v6a4 4 0 01-8 0V2z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 4H3v2a3 3 0 003 3M14 4h3v2a3 3 0 01-3 3M8 14h4M10 11v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
    };
    return `<svg class="stat-icon" viewBox="0 0 20 20" width="16" height="16">${paths[name]||''}</svg>`;
}

/* ---- Avatar helper ---- */

function avatarHtml(rider, cls) {
    const c = cls || 'avatar';
    return rider.avatar_url
        ? `<img src="${rider.avatar_url}" alt="${rider.name}" class="${c}">`
        : `<div class="${c} placeholder">${rider.name.charAt(0)}</div>`;
}

/* ---- Rider color assignment (stable by strava_id) ---- */

function ensureColorMap(riders) {
    if (colorMap) return colorMap;
    colorMap = {};
    const sorted = [...riders].sort((a, b) => a.strava_id - b.strava_id);
    sorted.forEach((r, i) => {
        colorMap[r.strava_id] = RIDER_COLORS[i % RIDER_COLORS.length];
        colorMap[r.name] = RIDER_COLORS[i % RIDER_COLORS.length];
    });
    return colorMap;
}

function riderColor(rider) {
    if (!colorMap) return RIDER_COLORS[0];
    return colorMap[rider.strava_id] || colorMap[rider.name] || RIDER_COLORS[0];
}

function sortedByColor(riders) {
    return [...riders].sort((a, b) => a.strava_id - b.strava_id);
}

/* ---- Theme color reader ---- */

function getThemeColors() {
    const cs = getComputedStyle(document.documentElement);
    return {
        text: cs.getPropertyValue('--text').trim() || '#f1f5f9',
        muted: cs.getPropertyValue('--text-muted').trim() || '#94a3b8',
        border: cs.getPropertyValue('--border').trim() || '#475569',
    };
}
