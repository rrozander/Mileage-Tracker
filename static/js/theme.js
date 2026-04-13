/* Dark / light mode toggle with localStorage persistence. */

function initTheme() {
    const saved = localStorage.getItem('mileage-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('mileage-theme', next);
    updateChartTheme();
}

document.getElementById('themeToggle').addEventListener('click', toggleTheme);
initTheme();
