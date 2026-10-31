const loginView = document.querySelector("#login-view");
const dashboardView = document.querySelector("#dashboard-view");
const loginForm = document.querySelector("#login-form");
const passwordInput = document.querySelector("#password");
const loginError = document.querySelector("#login-error");
const togglePasswordButton = document.querySelector("#toggle-password");
const logoutButton = document.querySelector("#logout-button");
const runButton = document.querySelector("#run-button");
const refreshButton = document.querySelector("#refresh-button");
const reloadAppsButton = document.querySelector("#reload-apps-button");
const refreshLogsButton = document.querySelector("#refresh-logs-button");
const runStatus = document.querySelector("#run-status");
const runDetails = document.querySelector("#run-details");
const nextAutoRun = document.querySelector("#next-auto-run");
const statusDot = document.querySelector("#status-dot");
const actionMessage = document.querySelector("#action-message");
const appsList = document.querySelector("#apps-list");
const debugLog = document.querySelector("#debug-log");
const logNote = document.querySelector("#log-note");

let dashboardPoll = null;

const PASSWORD_KEY = "marketingBotApiPassword";

function basicAuthorization(password) {
  const credentials = new TextEncoder().encode(`admin:${password}`);
  let binary = "";
  credentials.forEach((byte) => { binary += String.fromCharCode(byte); });
  return `Basic ${btoa(binary)}`;
}

async function apiFetch(path, options = {}) {
  const password = sessionStorage.getItem(PASSWORD_KEY);
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", basicAuthorization(password || ""));
  headers.set("X-Marketing-Bot-Client", "website");
  const response = await fetch(path, { ...options, headers });

  if (response.status === 401) {
    showLogin("Your password is no longer valid. Please sign in again.");
    throw new Error("Authentication failed");
  }

  return response;
}

function showLogin(message = "") {
  stopDashboardPolling();
  sessionStorage.removeItem(PASSWORD_KEY);
  dashboardView.hidden = true;
  loginView.hidden = false;
  loginError.textContent = message;
  loginError.hidden = !message;
  passwordInput.value = "";
  passwordInput.focus();
}

function showDashboard() {
  loginView.hidden = true;
  dashboardView.hidden = false;
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

function renderRun(run) {
  runStatus.textContent = run.status.charAt(0).toUpperCase() + run.status.slice(1);
  statusDot.className = `status-dot ${run.status}`;
  runButton.disabled = run.status === "running";
  document.querySelectorAll(".app-run-button").forEach((button) => {
    button.disabled = run.status === "running" || button.dataset.enabled !== "true";
  });
  nextAutoRun.textContent = run.nextAutoRunAt
    ? formatDate(run.nextAutoRunAt)
    : "Not scheduled";

  if (run.status === "idle") {
    runDetails.textContent = "No automation has been started from this API process.";
  } else if (run.status === "running") {
    runDetails.textContent = `Started ${formatDate(run.startedAt)} · PID ${run.pid}`;
  } else {
    runDetails.textContent = `Finished ${formatDate(run.finishedAt)} · Exit code ${run.exitCode}`;
  }
}

async function loadRunStatus() {
  const response = await apiFetch("/automation/run");
  if (!response.ok) throw new Error("Could not load automation status");
  renderRun(await response.json());
}

async function loadLogs() {
  const response = await apiFetch("/automation/logs?lines=200");
  if (!response.ok) throw new Error("Could not load automation logs");
  const body = await response.json();
  logNote.className = "log-note";
  const wasNearBottom = debugLog.scrollHeight - debugLog.scrollTop - debugLog.clientHeight < 40;
  debugLog.textContent = body.lines.length ? body.lines.join("\n") : "No runner output yet.";
  logNote.textContent = body.truncated
    ? "Showing the latest 200 lines. Older output is hidden."
    : "Latest website-triggered runner output.";
  if (wasNearBottom) debugLog.scrollTop = debugLog.scrollHeight;
}

function stopDashboardPolling() {
  if (dashboardPoll !== null) window.clearInterval(dashboardPoll);
  dashboardPoll = null;
}

function startDashboardPolling() {
  stopDashboardPolling();
  dashboardPoll = window.setInterval(async () => {
    if (dashboardView.hidden || document.hidden) return;
    await Promise.allSettled([loadRunStatus(), loadLogs()]);
  }, 3000);
}

function createPipelineButton(app, pipeline, label) {
  const button = document.createElement("button");
  button.className = "app-run-button";
  button.type = "button";
  button.textContent = label;
  button.dataset.enabled = String(app.enabled);
  button.disabled = !app.enabled || runStatus.textContent.toLowerCase() === "running";
  button.addEventListener("click", () => runAppPipeline(app, pipeline, button));
  return button;
}

function createAppCard(app) {
  const card = document.createElement("article");
  card.className = "app-card";

  const title = document.createElement("h3");
  title.textContent = app.appName;

  const description = document.createElement("p");
  description.textContent = app.appDescription || "No description configured.";

  const badge = document.createElement("span");
  badge.className = `badge${app.enabled ? "" : " disabled"}`;
  badge.textContent = app.enabled ? "Enabled" : "Disabled";

  const actions = document.createElement("div");
  actions.className = "app-actions";

  const buttons = document.createElement("div");
  buttons.className = "app-buttons";

  const toggleButton = document.createElement("button");
  toggleButton.className = "app-toggle-button";
  toggleButton.type = "button";
  toggleButton.textContent = app.enabled ? "Disable" : "Enable";
  toggleButton.addEventListener("click", () => toggleApp(app, toggleButton));

  const mainPipelineButton = createPipelineButton(app, "random", "Run main pipeline");
  const slideshowButton = createPipelineButton(app, "slideshow", "Run slideshow");
  const videoButton = createPipelineButton(app, "video", "Run video");

  buttons.append(toggleButton, mainPipelineButton, slideshowButton, videoButton);
  actions.append(badge, buttons);
  card.append(title, description, actions);
  return card;
}

async function toggleApp(app, button) {
  const enabled = !app.enabled;
  button.disabled = true;
  actionMessage.className = "message";
  actionMessage.textContent = `${enabled ? "Enabling" : "Disabling"} ${app.appName}…`;

  try {
    const response = await apiFetch(`/apps/${encodeURIComponent(app.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || `Could not update ${app.appName}`);
    actionMessage.textContent = `${app.appName} is now ${body.enabled ? "enabled" : "disabled"}.`;
    await loadApps();
  } catch (error) {
    button.disabled = false;
    actionMessage.textContent = error.message;
    actionMessage.className = "message error";
  }
}

async function runAppPipeline(app, pipeline, button) {
  button.disabled = true;
  actionMessage.className = "message";
  const pipelineLabel = pipeline === "random"
    ? "main pipeline"
    : `${pipeline} pipeline`;
  actionMessage.textContent = `Starting ${pipelineLabel} for ${app.appName}…`;

  try {
    const query = new URLSearchParams({ pipeline });
    const response = await apiFetch(`/automation/apps/${encodeURIComponent(app.id)}/run?${query}`, {
      method: "POST",
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || `Could not start ${app.appName}`);
    renderRun(body);
    const resultLabel = pipeline === "random"
      ? "Main"
      : pipeline === "video" ? "Video" : "Slideshow";
    actionMessage.textContent = `${resultLabel} pipeline started for ${app.appName}.`;
  } catch (error) {
    actionMessage.textContent = error.message;
    actionMessage.className = "message error";
    await loadRunStatus().catch(() => {});
  }
}

async function loadApps() {
  appsList.textContent = "Loading apps…";
  const response = await apiFetch("/apps");
  if (!response.ok) throw new Error("Could not load configured apps");

  const apps = await response.json();
  appsList.replaceChildren(...apps.map(createAppCard));
  if (!apps.length) appsList.textContent = "No apps are configured.";
}

async function loadDashboard() {
  showDashboard();
  actionMessage.textContent = "";
  try {
    await Promise.all([loadRunStatus(), loadApps(), loadLogs()]);
    startDashboardPolling();
  } catch (error) {
    if (dashboardView.hidden) return;
    actionMessage.textContent = error.message;
    actionMessage.className = "message error";
  }
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.hidden = true;
  sessionStorage.setItem(PASSWORD_KEY, passwordInput.value);

  try {
    const response = await apiFetch("/health");
    if (!response.ok) throw new Error("The API is unavailable");
    await loadDashboard();
  } catch (error) {
    if (loginError.hidden) showLogin(error.message);
  }
});

togglePasswordButton.addEventListener("click", () => {
  const showing = passwordInput.type === "text";
  passwordInput.type = showing ? "password" : "text";
  togglePasswordButton.textContent = showing ? "Show" : "Hide";
});

logoutButton.addEventListener("click", () => showLogin());
refreshButton.addEventListener("click", () => loadRunStatus().catch((error) => {
  actionMessage.textContent = error.message;
  actionMessage.className = "message error";
}));
reloadAppsButton.addEventListener("click", () => loadApps().catch((error) => {
  actionMessage.textContent = error.message;
  actionMessage.className = "message error";
}));
refreshLogsButton.addEventListener("click", () => loadLogs().catch((error) => {
  logNote.textContent = error.message;
  logNote.className = "log-note error";
}));

runButton.addEventListener("click", async () => {
  runButton.disabled = true;
  actionMessage.className = "message";
  actionMessage.textContent = "Starting automation…";
  try {
    const response = await apiFetch("/automation/run", { method: "POST" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Could not start automation");
    renderRun(body);
    actionMessage.textContent = "Automation started successfully.";
    await loadLogs();
  } catch (error) {
    actionMessage.textContent = error.message;
    actionMessage.className = "message error";
    await loadRunStatus().catch(() => {});
  }
});

if (sessionStorage.getItem(PASSWORD_KEY)) {
  loadDashboard();
} else {
  showLogin();
}
