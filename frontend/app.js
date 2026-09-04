const API_BASE = "/api";
let services = [];

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function calculateMetrics(service) {
    const history = service.history ?? [];
    if (history.length === 0) {
        return { status: "pending", latest: null, average: null, uptime: null };
    }
    const successful = history.filter((check) => check.status === "online");
    const times = successful
        .map((check) => check.response_time_ms)
        .filter((time) => Number.isFinite(time));
    return {
        status: history.at(-1).status,
        latest: history.at(-1).response_time_ms,
        average: times.length
            ? Math.round(times.reduce((sum, time) => sum + time, 0) / times.length)
            : null,
        uptime: ((successful.length / history.length) * 100).toFixed(1)
    };
}

function valueOrDash(value, suffix = "") {
    return value === null || value === undefined ? "—" : `${value}${suffix}`;
}

function renderServices() {
    const list = document.querySelector("#service-list");
    if (services.length === 0) {
        list.innerHTML = '<div class="empty-state">No endpoints yet. Add your first monitor above.</div>';
    } else {
        list.innerHTML = services.map((service) => {
            const metrics = calculateMetrics(service);
            const history = service.history ?? [];
            const bars = history.length
                ? `<div class="history" title="Last ${history.length} checks">${history.map(
                    (check) => `<span class="${check.status === "online" ? "" : "failed"}"></span>`
                ).join("")}</div>`
                : '<span class="history-empty">Waiting for the first check</span>';
            return `
                <article class="service-card">
                    <div class="card-top">
                        <span class="status ${metrics.status}">${metrics.status.toUpperCase()}</span>
                        <button class="delete-button" data-id="${service.id}" type="button">Remove</button>
                    </div>
                    <h3>${escapeHtml(service.name)}</h3>
                    <a class="service-url" href="${escapeHtml(service.url)}" target="_blank" rel="noopener noreferrer">
                        ${escapeHtml(service.url)}
                    </a>
                    <div class="metrics">
                        <div class="metric"><span>Latest</span><strong>${valueOrDash(metrics.latest, " ms")}</strong></div>
                        <div class="metric"><span>Average</span><strong>${valueOrDash(metrics.average, " ms")}</strong></div>
                        <div class="metric"><span>Recent uptime</span><strong>${valueOrDash(metrics.uptime, "%")}</strong></div>
                    </div>
                    ${bars}
                </article>`;
        }).join("");
    }
    updateSummary();
}

function updateSummary() {
    const metrics = services.map(calculateMetrics);
    const online = metrics.filter((item) => item.status === "online").length;
    const offline = metrics.filter((item) => item.status === "offline").length;
    const latencies = metrics.map((item) => item.latest).filter(Number.isFinite);
    const average = latencies.length
        ? Math.round(latencies.reduce((sum, value) => sum + value, 0) / latencies.length)
        : null;
    document.querySelector("#total-services").textContent = services.length;
    document.querySelector("#online-services").textContent = online;
    document.querySelector("#offline-services").textContent = offline;
    document.querySelector("#average-latency").textContent = valueOrDash(average, " ms");
}

function setConnectionStatus(message, isError = false) {
    const status = document.querySelector("#api-status");
    status.textContent = message;
    status.classList.toggle("error", isError);
}

function showFormMessage(message, isError = false) {
    const element = document.querySelector("#form-message");
    element.textContent = message;
    element.classList.toggle("error", isError);
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers ?? {}) }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error ?? `Request failed (${response.status}).`);
    return payload;
}

async function loadServices() {
    try {
        const payload = await apiRequest("/endpoints");
        services = payload.services;
        renderServices();
        setConnectionStatus("API connected");
    } catch (error) {
        setConnectionStatus("API unavailable", true);
        document.querySelector("#service-list").innerHTML =
            `<div class="empty-state">${escapeHtml(error.message)} Start CloudPulse with <code>python -m backend.server</code>.</div>`;
    }
}

async function addMonitor(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    showFormMessage("Checking endpoint…");
    try {
        await apiRequest("/endpoints", {
            method: "POST",
            body: JSON.stringify({
                name: document.querySelector("#service-name").value.trim(),
                url: document.querySelector("#service-url").value.trim()
            })
        });
        form.reset();
        showFormMessage("Monitor added successfully.");
        await loadServices();
    } catch (error) {
        showFormMessage(error.message, true);
    } finally {
        submitButton.disabled = false;
    }
}

async function runChecks() {
    const button = document.querySelector("#refresh-button");
    button.disabled = true;
    button.textContent = "Checking…";
    try {
        const payload = await apiRequest("/checks/run", { method: "POST" });
        services = payload.services;
        renderServices();
        document.querySelector("#last-updated").textContent =
            `Updated ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
        setConnectionStatus("API connected");
    } catch (error) {
        setConnectionStatus(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Run checks";
    }
}

async function removeMonitor(endpointId) {
    if (!window.confirm("Remove this monitor and its check history?")) return;
    try {
        await apiRequest(`/endpoints/${encodeURIComponent(endpointId)}`, { method: "DELETE" });
        services = services.filter((service) => service.id !== endpointId);
        renderServices();
    } catch (error) {
        setConnectionStatus(error.message, true);
    }
}

document.querySelector("#monitor-form").addEventListener("submit", addMonitor);
document.querySelector("#refresh-button").addEventListener("click", runChecks);
document.querySelector("#service-list").addEventListener("click", (event) => {
    const button = event.target.closest(".delete-button");
    if (button) removeMonitor(button.dataset.id);
});

loadServices();
