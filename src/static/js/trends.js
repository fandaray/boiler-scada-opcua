// Тренды уровня и температуры из истории SQLite (GET /api/history).
const TREND_REFRESH_MS = 10000;
const css = getComputedStyle(document.documentElement);
const color = (name) => css.getPropertyValue(name).trim();

const trendNote = document.getElementById("trendNote");
const trendChart = new Chart(document.getElementById("trendChart"), {
  type: "line",
  data: {
    labels: [],
    datasets: [
      { label: "Уровень, %", yAxisID: "yLevel", borderColor: color("--cold"), data: [] },
      { label: "Уставка уровня", yAxisID: "yLevel", borderColor: color("--cold"), borderDash: [5, 4], borderWidth: 1, data: [] },
      { label: "Температура, °C", yAxisID: "yTemp", borderColor: color("--hot"), data: [] },
      { label: "Уставка температуры", yAxisID: "yTemp", borderColor: color("--hot"), borderDash: [5, 4], borderWidth: 1, data: [] },
    ],
  },
  options: {
    animation: false,
    maintainAspectRatio: false,
    elements: { point: { radius: 0 }, line: { borderWidth: 2, tension: 0.2 } },
    interaction: { mode: "index", intersect: false },
    plugins: { legend: { labels: { color: color("--text"), boxWidth: 14 } } },
    scales: {
      x: { ticks: { color: color("--text-dim"), maxTicksLimit: 8 }, grid: { color: color("--line") } },
      yLevel: { position: "left", min: 0, max: 100, title: { display: true, text: "%", color: color("--text-dim") },
                ticks: { color: color("--text-dim") }, grid: { color: color("--line") } },
      yTemp: { position: "right", min: 0, max: 100, title: { display: true, text: "°C", color: color("--text-dim") },
               ticks: { color: color("--text-dim") }, grid: { drawOnChartArea: false } },
    },
  },
});

async function refreshTrends() {
  try {
    const res = await fetch("/api/history?minutes=15");
    const data = await res.json();
    const rows = data.rows || [];
    trendNote.textContent = rows.length ? `${rows.length} точек · обновление каждые 10 с` : (data.note || "нет данных");
    trendChart.data.labels = rows.map((r) => r.timestamp.slice(11));
    const keys = ["level", "level_setpoint", "temperature", "temperature_setpoint"];
    keys.forEach((k, i) => (trendChart.data.datasets[i].data = rows.map((r) => r[k])));
    trendChart.update();
  } catch (err) {
    trendNote.textContent = "история недоступна";
  }
}

refreshTrends();
setInterval(refreshTrends, TREND_REFRESH_MS);
