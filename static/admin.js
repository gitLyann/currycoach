"use strict";
const keyInput = document.getElementById("admin-key");
const errorBox = document.getElementById("auth-error");
const dashboard = document.getElementById("dashboard");
const theme = "currycoach";
keyInput.value = sessionStorage.getItem("currycoach-admin-key") || "";

function setText(id, value) { document.getElementById(id).textContent = String(value); }
function renderIntentChart(items) {
  const chart = document.getElementById("intent-chart");
  chart.replaceChildren();
  if (!items || !items.length) {
    const empty = document.createElement("p"); empty.className = "empty-state"; empty.textContent = "Belum ada data intent."; chart.appendChild(empty); return;
  }
  const max = Math.max(...items.map((item) => Number(item.total)), 1);
  items.forEach((item) => {
    const row = document.createElement("div"); row.className = "bar-row";
    const label = document.createElement("span"); label.className = "bar-label"; label.textContent = item.intent || "Tidak diketahui";
    const track = document.createElement("div"); track.className = "bar-track";
    const fill = document.createElement("div"); fill.className = "bar-fill"; fill.style.width = `${Math.max(2, Number(item.total) / max * 100)}%`; track.appendChild(fill);
    const value = document.createElement("span"); value.className = "bar-value"; value.textContent = item.total;
    row.append(label, track, value); chart.appendChild(row);
  });
}
function renderUnknown(items) {
  const body = document.getElementById("unknown-questions"); body.replaceChildren();
  if (!items || !items.length) {
    const row = document.createElement("tr"); const cell = document.createElement("td"); cell.colSpan = 2; cell.className = "empty-state"; cell.textContent = "Belum ada pertanyaan fallback."; row.appendChild(cell); body.appendChild(row); return;
  }
  items.forEach((item) => {
    const row = document.createElement("tr"); const question = document.createElement("td"); question.textContent = item.text;
    const count = document.createElement("td"); count.textContent = item.total; row.append(question, count); body.appendChild(row);
  });
}
async function loadDashboard() {
  errorBox.textContent = "";
  const headers = {};
  if (keyInput.value.trim()) headers["X-Admin-Key"] = keyInput.value.trim();
  try {
    const response = await fetch(`/api/stats/${theme}`, { headers });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Tidak dapat mengambil statistik.");
    sessionStorage.setItem("currycoach-admin-key", keyInput.value.trim());
    const total = Number(data.total_questions || 0);
    const recognized = Number(data.recognized || 0);
    const unrecognized = Number(data.unrecognized || 0);
    const rate = total ? recognized / total * 100 : 0;
    setText("total-questions", total); setText("recognized", recognized); setText("unrecognized", unrecognized); setText("sessions", data.sessions || 0);
    setText("recognized-rate", `${rate.toFixed(1)}% dari pertanyaan`);
    setText("fallback-rate", `${(total ? unrecognized / total * 100 : 0).toFixed(1)}% dari pertanyaan`);
    setText("recognition-percent", `${rate.toFixed(0)}%`);
    setText("legend-recognized", recognized); setText("legend-unrecognized", unrecognized);
    document.getElementById("recognition-donut").style.background = `conic-gradient(#1D428A ${rate * 3.6}deg, #FFC72C 0deg)`;
    renderIntentChart(data.intent_stats || []); renderUnknown(data.unrecognized_questions || []);
    dashboard.hidden = false;
  } catch (error) {
    errorBox.textContent = error.message;
    dashboard.hidden = true;
  }
}
document.getElementById("load-dashboard").addEventListener("click", loadDashboard);
document.getElementById("refresh-stats").addEventListener("click", loadDashboard);
keyInput.addEventListener("keydown", (event) => { if (event.key === "Enter") loadDashboard(); });
loadDashboard();
