function isoFromLocal(dtLocal) {
  if (!dtLocal) return null;
  try {
    return new Date(dtLocal).toISOString();
  } catch {
    return null;
  }
}

async function loadEvents() {
  const ip = document.getElementById("ip-filter").value.trim();
  const level = document.getElementById("level-filter").value.trim();
  const sinceLocal = document.getElementById("since-filter").value;
  const sinceIso = isoFromLocal(sinceLocal);

  const params = new URLSearchParams();
  if (ip) params.set("ip", ip);
  if (level) params.set("level", level);
  if (sinceIso) params.set("since", sinceIso);

  const res = await fetch(`/api/events?${params.toString()}`);
  const data = await res.json();
  const tbody = document.getElementById("events-body");
  tbody.innerHTML = "";
  data.forEach((e) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.timestamp}</td>
      <td>${e.miner_ip || "—"}</td>
      <td>${e.level}</td>
      <td>${e.source}</td>
      <td>${e.message}</td>`;
    if (e.level === "ERROR") tr.style.background = "#ffecec";
    tbody.appendChild(tr);
  });
}

async function loadLive() {
  const ip = document.getElementById("ip-filter").value.trim();
  if (!ip) {
    alert("Enter a Miner IP to load live logs.html");
    return;
  }
  const res = await fetch(`/api/miner/${encodeURIComponent(ip)}/logs`);
  const payload = await res.json();
  const tbody = document.getElementById("live-body");
  tbody.innerHTML = "";
  if (!payload.ok) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="3">Error: ${
      payload.error || "failed to fetch logs.html"
    }</td>`;
    tbody.appendChild(tr);
    return;
  }
  payload.entries.forEach((e) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${e.ts || "—"}</td>
      <td>${e.level || "INFO"}</td>
      <td>${e.message || ""}</td>
    `;
    tbody.appendChild(tr);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("load-events").addEventListener("click", loadEvents);
  document.getElementById("load-live").addEventListener("click", loadLive);
  // initial load of events
  loadEvents();
  // auto-refresh events every 30s
  setInterval(loadEvents, 30000);
});
