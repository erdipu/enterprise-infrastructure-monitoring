// ==============================================================================
// Enterprise Infrastructure Monitoring & Incident Management Portal - JS
// ==============================================================================

const API_BASE = "/api/v1";
let currentIncident = null;
let incidentModalInstance = null;
let addMonitorModalInstance = null;
let activePollingTimer = null;

// On Page Load
document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("noc_token");
  const username = localStorage.getItem("noc_username");
  
  const incEl = document.getElementById("incidentModal");
  if (incEl) incidentModalInstance = new bootstrap.Modal(incEl);

  const addMonEl = document.getElementById("addMonitorModal");
  if (addMonEl) addMonitorModalInstance = new bootstrap.Modal(addMonEl);

  if (token) {
    showAppView(username);
    loadDashboard();
    startAutoRefresh();
  } else {
    showLoginView();
  }
});

// View Toggle
function showLoginView() {
  document.getElementById("loginView").classList.remove("d-none");
  document.getElementById("appContainer").classList.add("d-none");
  document.getElementById("userInfoNav").classList.add("d-none");
  document.getElementById("userInfoNav").classList.remove("d-flex");
  if (activePollingTimer) clearInterval(activePollingTimer);
}

function showAppView(username) {
  document.getElementById("loginView").classList.add("d-none");
  document.getElementById("appContainer").classList.remove("d-none");
  document.getElementById("userInfoNav").classList.remove("d-none");
  document.getElementById("userInfoNav").classList.add("d-flex");
  document.getElementById("navUsername").innerText = username || "Operator";
}

// Authentication
async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;
  const alertBox = document.getElementById("loginAlert");
  alertBox.classList.add("d-none");

  try {
    const res = await fetch(`${API_BASE}/auth/login-json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }

    const data = await res.json();
    localStorage.setItem("noc_token", data.access_token);
    localStorage.setItem("noc_username", data.username);
    localStorage.setItem("noc_role", data.role);

    showAppView(data.username);
    loadDashboard();
    startAutoRefresh();
  } catch (err) {
    alertBox.innerText = err.message;
    alertBox.classList.remove("d-none");
  }
}

function logout() {
  localStorage.removeItem("noc_token");
  localStorage.removeItem("noc_username");
  localStorage.removeItem("noc_role");
  showLoginView();
}

function authHeaders() {
  const token = localStorage.getItem("noc_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {})
  };
}

// Dashboard Overview
async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/reports/summary`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("statTotalSystems").innerText = data.total_servers;
    document.getElementById("statSystemsUp").innerText = data.servers_up;
    document.getElementById("statSystemsDown").innerText = data.servers_down;
    document.getElementById("statAvailability").innerText = `${data.overall_availability_pct}%`;
    document.getElementById("statOpenIncidents").innerText = data.open_incidents;
    document.getElementById("statAvgMttr").innerText = `${data.avg_mttr_minutes} m`;

    document.getElementById("statP1Count").innerText = data.p1_count;
    document.getElementById("statP2Count").innerText = data.p2_count;
    document.getElementById("statP3Count").innerText = data.p3_count;
    document.getElementById("statP4Count").innerText = data.p4_count;

    // Top Systems
    const tbody = document.getElementById("topSystemsTableBody");
    tbody.innerHTML = "";
    if (!data.top_alerting_systems || data.top_alerting_systems.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center text-secondary py-3">No incident trends logged.</td></tr>`;
    } else {
      data.top_alerting_systems.forEach(item => {
        tbody.innerHTML += `
          <tr>
            <td class="hostname-highlight"><i class="bi bi-hdd-network me-2 text-info"></i>${item.system}</td>
            <td class="text-warning fw-bold">${item.incidents}</td>
            <td><span class="badge ${item.incidents > 2 ? 'badge-p1' : 'badge-p3'}">Elevated Failure Rate</span></td>
          </tr>
        `;
      });
    }
  } catch (err) {
    console.error("Failed to load dashboard:", err);
  }
}

// Servers Inventory
async function loadServers() {
  try {
    const res = await fetch(`${API_BASE}/servers/`, { headers: authHeaders() });
    if (!res.ok) return;
    const servers = await res.json();

    const tbody = document.getElementById("serversTableBody");
    tbody.innerHTML = "";
    if (servers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-secondary py-3">No registered servers. Click "+ Add Server" to register one.</td></tr>`;
      return;
    }

    servers.forEach(s => {
      const statusBadge = s.status === "UP" ? "badge-up" : (s.status === "DOWN" ? "badge-down" : "badge-warning");
      const osIcon = s.os_type === "linux" ? "bi-ubuntu" : "bi-windows";
      const lastCheck = s.last_check ? new Date(s.last_check).toLocaleTimeString() : "--";

      tbody.innerHTML += `
        <tr>
          <td class="hostname-highlight"><i class="bi bi-hdd-network me-2 text-info"></i>${s.hostname}</td>
          <td><code>${s.ip_address}</code></td>
          <td><i class="bi ${osIcon} me-1 text-info"></i>${s.os_type.toUpperCase()}</td>
          <td><span class="badge bg-dark border border-secondary">${s.environment}</span></td>
          <td><span class="badge ${statusBadge}">${s.status}</span></td>
          <td>${s.cpu_cores} vCPU</td>
          <td>${s.total_ram_gb} GB</td>
          <td>${s.total_disk_gb} GB</td>
          <td class="text-secondary small">${lastCheck}</td>
          <td>
            <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="deleteServer(${s.id}, '${s.hostname}')" title="Delete Server">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
    });
  } catch (err) {
    console.error("Failed to load servers:", err);
  }
}

// Synthetic Web & API Targets (UptimeRobot Style)
async function loadTargets() {
  try {
    const res = await fetch(`${API_BASE}/targets/`, { headers: authHeaders() });
    if (!res.ok) return;
    const targets = await res.json();

    const tbody = document.getElementById("targetsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (targets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-secondary py-3">No synthetic monitors registered. Click "+ Add URL / Website" above.</td></tr>`;
      return;
    }

    targets.forEach(t => {
      const statusBadge = t.status === "UP" ? "badge-up" : (t.status === "DOWN" ? "badge-down" : "badge-warning");
      const typeBadge = t.target_type === "website" ? "bg-primary" : "bg-info text-dark";
      const lastCheck = t.last_check ? new Date(t.last_check).toLocaleTimeString() : "--";
      const latencyStr = (t.status === "UP" && t.last_response_time_ms && t.last_response_time_ms > 0) ? `${parseFloat(t.last_response_time_ms).toFixed(1)} ms` : "<span class=\"text-danger fw-bold\">0 ms (Timeout)</span>";

      tbody.innerHTML += `
        <tr>
          <td class="hostname-highlight"><i class="bi bi-globe me-2 text-info"></i>${t.name}</td>
          <td><code>${t.url_or_host}</code></td>
          <td><span class="badge ${typeBadge}">${t.target_type.toUpperCase()}</span></td>
          <td><span class="badge ${statusBadge}">${t.status}</span></td>
          <td class="fw-semibold text-light">${latencyStr}</td>
          <td>${t.check_interval_sec}s</td>
          <td class="text-secondary small">${lastCheck}</td>
          <td>
            <button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="deleteTarget(${t.id}, '${t.name}')" title="Delete Monitor">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        </tr>
      `;
    });
  } catch (err) {
    console.error("Failed to load targets:", err);
  }
}

// Alerts Feed
async function loadAlerts() {
  try {
    const res = await fetch(`${API_BASE}/alerts/`, { headers: authHeaders() });
    if (!res.ok) return;
    const alerts = await res.json();

    const tbody = document.getElementById("alertsTableBody");
    tbody.innerHTML = "";
    if (alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-secondary py-3">No active Prometheus alerts recorded.</td></tr>`;
      return;
    }

    alerts.forEach(a => {
      const pBadge = `badge-${a.priority.toLowerCase()}`;
      const statusBadge = a.status === "firing" ? "badge-down" : "badge-up";
      const timeStr = a.started_at ? new Date(a.started_at).toLocaleString() : "--";

      tbody.innerHTML += `
        <tr>
          <td class="fw-semibold text-light">${a.alert_name}</td>
          <td><code>${a.target_name}</code></td>
          <td><span class="badge bg-secondary">${a.severity}</span></td>
          <td><span class="badge ${pBadge}">${a.priority}</span></td>
          <td><span class="badge ${statusBadge}">${a.status.toUpperCase()}</span></td>
          <td class="text-secondary small">${a.summary}</td>
          <td class="text-secondary small">${timeStr}</td>
        </tr>
      `;
    });
  } catch (err) {
    console.error("Failed to load alerts:", err);
  }
}

// Incidents Queue
async function loadIncidents() {
  const filter = document.getElementById("incidentStatusFilter").value;
  const url = filter ? `${API_BASE}/incidents/?status=${filter}` : `${API_BASE}/incidents/`;

  try {
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const incidents = await res.json();

    const tbody = document.getElementById("incidentsTableBody");
    tbody.innerHTML = "";
    if (incidents.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-secondary py-3">No incidents matching criteria.</td></tr>`;
      return;
    }

    incidents.forEach(inc => {
      const pBadge = `badge-${inc.priority.toLowerCase()}`;
      let sBadge = "badge-open";
      if (inc.status === "ACKNOWLEDGED") sBadge = "badge-ack";
      if (inc.status === "IN_PROGRESS") sBadge = "badge-prog";
      if (inc.status === "RESOLVED") sBadge = "badge-resolved";

      const timeStr = inc.created_at ? new Date(inc.created_at).toLocaleTimeString() : "--";

      tbody.innerHTML += `
        <tr>
          <td class="fw-bold text-light">${inc.incident_number}</td>
          <td class="fw-semibold text-light">${inc.title}</td>
          <td><span class="badge ${pBadge}">${inc.priority}</span></td>
          <td>${inc.severity}</td>
          <td><code>${inc.target_system}</code></td>
          <td><span class="badge ${sBadge}">${inc.status}</span></td>
          <td class="text-secondary small">${timeStr}</td>
          <td>
            <button class="btn btn-outline-primary btn-sm py-0 px-2" onclick="openIncidentModal(${inc.id})">
              <i class="bi bi-pencil-square me-1"></i>Triage
            </button>
          </td>
        </tr>
      `;
    });
  } catch (err) {
    console.error("Failed to load incidents:", err);
  }
}

// Incident Modal & Triage Actions
async function openIncidentModal(incidentId) {
  try {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}`, { headers: authHeaders() });
    if (!res.ok) return;
    currentIncident = await res.json();

    document.getElementById("modalIncidentNumber").innerText = currentIncident.incident_number;
    document.getElementById("modalIncidentTitle").innerText = currentIncident.title;
    document.getElementById("modalPriorityBadge").className = `badge badge-${currentIncident.priority.toLowerCase()}`;
    document.getElementById("modalPriorityBadge").innerText = currentIncident.priority;
    document.getElementById("modalTargetSystem").innerText = currentIncident.target_system;

    let sBadge = "badge-open";
    if (currentIncident.status === "ACKNOWLEDGED") sBadge = "badge-ack";
    if (currentIncident.status === "IN_PROGRESS") sBadge = "badge-prog";
    if (currentIncident.status === "RESOLVED") sBadge = "badge-resolved";
    document.getElementById("modalStatusBadge").className = `badge ${sBadge}`;
    document.getElementById("modalStatusBadge").innerText = currentIncident.status;

    document.getElementById("modalCreatedAt").innerText = new Date(currentIncident.created_at).toLocaleString();
    document.getElementById("modalDescription").innerText = currentIncident.description;
    document.getElementById("modalRootCause").value = currentIncident.root_cause || "";
    document.getElementById("modalResolutionNotes").value = currentIncident.resolution_notes || "";

    // Comments
    renderModalComments(currentIncident.comments || []);

    incidentModalInstance.show();
  } catch (err) {
    console.error("Failed to open incident modal:", err);
  }
}

function renderModalComments(comments) {
  const container = document.getElementById("modalCommentsContainer");
  container.innerHTML = "";
  if (comments.length === 0) {
    container.innerHTML = `<span class="text-secondary small">No comments logged yet.</span>`;
    return;
  }
  comments.forEach(c => {
    const time = new Date(c.created_at).toLocaleTimeString();
    container.innerHTML += `
      <div class="mb-1 text-light small border-bottom border-secondary pb-1">
        <span class="text-info fw-bold">[${time}]</span> ${c.comment}
      </div>
    `;
  });
}

async function updateIncidentStatus(newStatus) {
  if (!currentIncident) return;
  const rootCause = document.getElementById("modalRootCause").value.trim();
  const resolutionNotes = document.getElementById("modalResolutionNotes").value.trim();

  try {
    const res = await fetch(`${API_BASE}/incidents/${currentIncident.id}`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify({
        status: newStatus,
        root_cause: rootCause || null,
        resolution_notes: resolutionNotes || null
      })
    });

    if (!res.ok) {
      alert("Failed to update incident. Check permissions.");
      return;
    }

    currentIncident = await res.json();
    openIncidentModal(currentIncident.id);
    loadIncidents();
    loadDashboard();
  } catch (err) {
    console.error("Error updating incident:", err);
  }
}

async function submitComment() {
  if (!currentIncident) return;
  const input = document.getElementById("newCommentInput");
  const comment = input.value.trim();
  if (!comment) return;

  try {
    const res = await fetch(`${API_BASE}/incidents/${currentIncident.id}/comments`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ comment })
    });

    if (!res.ok) return;
    input.value = "";
    openIncidentModal(currentIncident.id);
  } catch (err) {
    console.error("Error submitting comment:", err);
  }
}

// Reports Pane
async function loadReports() {
  try {
    const res = await fetch(`${API_BASE}/reports/summary`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("reportAvailability").innerText = `${data.overall_availability_pct}%`;
    document.getElementById("reportAvgMttr").innerText = `${data.avg_mttr_minutes} min`;
    document.getElementById("reportTotalIncidents").innerText = data.total_incidents;
  } catch (err) {
    console.error("Failed to load reports:", err);
  }
}

function exportIncidentsCSV() {
  window.open(`${API_BASE}/reports/export/csv`, "_blank");
}

function refreshCurrentTab() {
  loadDashboard();
  loadServers();
  loadTargets();
  loadAlerts();
  loadIncidents();
  loadReports();
}

function startAutoRefresh() {
  if (activePollingTimer) clearInterval(activePollingTimer);
  activePollingTimer = setInterval(() => {
    loadDashboard();
  }, 15000); // 15-second refresh interval
}

// ----------------------------------------------------------------------------
// Dynamic Monitor Management (UptimeRobot Style)
// ----------------------------------------------------------------------------

function openAddMonitorModal(category = "website") {
  const catSelect = document.getElementById("monitorCategory");
  if (catSelect) catSelect.value = category;
  toggleMonitorFormFields();
  
  const nameEl = document.getElementById("monitorName");
  if (nameEl) nameEl.value = "";
  const urlEl = document.getElementById("monitorUrl");
  if (urlEl) urlEl.value = "";
  const ipEl = document.getElementById("serverIp");
  if (ipEl) ipEl.value = "";

  if (addMonitorModalInstance) {
    addMonitorModalInstance.show();
  } else {
    const modalEl = document.getElementById("addMonitorModal");
    if (modalEl) {
      addMonitorModalInstance = new bootstrap.Modal(modalEl);
      addMonitorModalInstance.show();
    }
  }
}

function toggleMonitorFormFields() {
  const cat = document.getElementById("monitorCategory").value;
  const webFields = document.getElementById("websiteFields");
  const srvFields = document.getElementById("serverFields");

  if (cat === "server") {
    webFields.style.display = "none";
    srvFields.style.display = "block";
    document.getElementById("addMonitorModalTitle").innerHTML = '<i class="bi bi-hdd-network text-primary me-2"></i>Add Infrastructure Server';
  } else {
    webFields.style.display = "block";
    srvFields.style.display = "none";
    document.getElementById("addMonitorModalTitle").innerHTML = '<i class="bi bi-globe2 text-success me-2"></i>Add Synthetic URL / Website';
  }
}

async function submitAddMonitor() {
  const category = document.getElementById("monitorCategory").value;
  const name = document.getElementById("monitorName").value.trim();

  if (!name) {
    alert("Please enter a monitor name");
    return;
  }

  try {
    if (category === "website") {
      const url = document.getElementById("monitorUrl").value.trim();
      const targetType = document.getElementById("monitorTargetType").value;
      const interval = parseInt(document.getElementById("monitorInterval").value) || 15;

      if (!url) {
        alert("Please enter a valid URL (e.g. https://example.com)");
        return;
      }

      const res = await fetch(`${API_BASE}/targets/`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          name: name,
          target_type: targetType,
          url_or_host: url,
          port: url.startsWith("https") ? 443 : 80,
          check_interval_sec: interval,
          expected_status_code: 200,
          status: "UP"
        })
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Failed to create synthetic monitor");
        return;
      }
    } else {
      const ip = document.getElementById("serverIp").value.trim();
      const os = document.getElementById("serverOs").value;
      const env = document.getElementById("serverEnv").value;

      if (!ip) {
        alert("Please enter an IP address");
        return;
      }

      const res = await fetch(`${API_BASE}/servers/`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          hostname: name,
          ip_address: ip,
          os_type: os,
          environment: env,
          status: "UP",
          cpu_cores: 2,
          total_ram_gb: 4.0,
          total_disk_gb: 100.0
        })
      });

      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Failed to create server");
        return;
      }
    }

    const modalEl = document.getElementById("addMonitorModal");
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) modal.hide();

    // Reload lists and dashboard stats
    loadServers();
    loadTargets();
    loadDashboard();
  } catch (err) {
    console.error("Failed to add monitor:", err);
    alert("An unexpected error occurred while adding the monitor.");
  }
}

async function deleteServer(id, hostname) {
  if (!confirm(`Are you sure you want to delete server '${hostname}'?`)) return;

  try {
    const res = await fetch(`${API_BASE}/servers/${id}`, {
      method: "DELETE",
      headers: authHeaders()
    });

    if (!res.ok) {
      alert("Failed to delete server");
      return;
    }

    loadServers();
    loadDashboard();
  } catch (err) {
    console.error("Error deleting server:", err);
  }
}

async function deleteTarget(id, name) {
  if (!confirm(`Are you sure you want to delete synthetic monitor '${name}'?`)) return;

  try {
    const res = await fetch(`${API_BASE}/targets/${id}`, {
      method: "DELETE",
      headers: authHeaders()
    });

    if (!res.ok) {
      alert("Failed to delete monitor");
      return;
    }

    loadTargets();
    loadDashboard();
  } catch (err) {
    console.error("Error deleting target:", err);
  }
}
