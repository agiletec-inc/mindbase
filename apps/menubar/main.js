const { app, Tray, Menu, BrowserWindow, shell, nativeImage, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");

const DEFAULT_REFRESH_MS = 15000;
const DEFAULT_ICON_DATA_URL =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAAAnUlEQVR42mNgoCZIT0//PwMDA8O/f/8GQkND4+HhYTgYGBj+//8/Dw4O/j8jIyMYGhqKqqqqQEJCwoKCgoyMjCCtra3Pz8/Y2Nj45OTk4eHh4f///0NGxgYGD4zMzMhJSUFOzs7AwMDA2NjY/j8/P1RUVFhZWSn29vZSEhLi19eXlZWFqaurm7w9fUlq6urlZSUkJ6enngFI5NDY2BgYGAPdCCxYcX1/gQAAAABJRU5ErkJggg==";

let tray;
let settingsWindow;
let settingsPath;
let settings = null;
let refreshTimer = null;

const state = {
  health: null,
  lastUpdated: null,
  error: null,
};

const templateIcon = () => {
  if (nativeImage.createFromNamedImage) {
    const named = nativeImage.createFromNamedImage("NSStatusAvailable");
    if (named && !named.isEmpty()) {
      return named;
    }
  }
  return nativeImage.createFromDataURL(DEFAULT_ICON_DATA_URL);
};

const getConfigDir = () => {
  return path.join(app.getPath("userData"), "mindbase-menubar");
};

const ensureSettings = () => {
  const configDir = getConfigDir();
  settingsPath = path.join(configDir, "settings.json");
  const defaultPath = path.join(__dirname, "config", "default-settings.json");

  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }
  if (!fs.existsSync(settingsPath)) {
    fs.copyFileSync(defaultPath, settingsPath);
  }
  const contents = fs.readFileSync(settingsPath, "utf-8");
  settings = JSON.parse(contents);
};

const persistSettings = (overrides) => {
  settings = { ...settings, ...overrides };
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
  scheduleRefresh();
};

const statusIcon = (status) => {
  switch (status) {
    case "healthy":
    case "running":
      return "🟢";
    case "degraded":
    case "warming":
      return "🟡";
    case "error":
    case "stopped":
      return "🔴";
    default:
      return "⚪️";
  }
};

const buildCollectorsMenu = () => {
  return settings.collectors.map((collector) => {
    const label = `${statusIcon(state.health?.status || "unknown")} ${collector.label}`;
    return {
      label,
      submenu: [
        { label: `Workspace: ${collector.workspace || "default"}`, enabled: false },
        { type: "separator" },
        {
          label: "Open Logs (CLI)",
          click: () => shell.openExternal("https://github.com/mindbasehq"),
        },
      ],
    };
  });
};

const buildPipelinesMenu = () => {
  return settings.pipelines.map((pipeline) => ({
    label: `${statusIcon(state.health?.status || "unknown")} ${pipeline.label}`,
    enabled: false,
  }));
};

const buildServicesMenu = () => {
  const services = state.health?.services || {};
  return Object.keys(services).map((name) => ({
    label: `${statusIcon(services[name])} ${name}`,
    enabled: false,
  }));
};

const buildMenu = () => {
  const template = [
    {
      label: "Open MindBase Dashboard",
      click: () => {
        const docsUrl = `${settings.apiBaseUrl.replace(/\/$/, "")}/docs`;
        shell.openExternal(docsUrl);
      },
    },
    { type: "separator" },
    {
      label: "Collectors",
      submenu: buildCollectorsMenu(),
    },
    {
      label: "Pipelines",
      submenu: buildPipelinesMenu(),
    },
    {
      label: "Services",
      submenu: buildServicesMenu(),
    },
    { type: "separator" },
    {
      label: state.lastUpdated
        ? `Last Updated: ${state.lastUpdated.toLocaleTimeString()}`
        : "Last Updated: --",
      enabled: false,
    },
    {
      label: state.error ? `Status: ${state.error}` : "Status: OK",
      enabled: false,
    },
    {
      label: "Refresh Now",
      click: () => refreshHealth(true),
    },
    { type: "separator" },
    {
      label: "Help",
      submenu: [
        {
          label: "Documentation",
          click: () =>
            shell.openExternal("https://github.com/kazuki0422/mindbase"),
        },
        {
          label: "Report Issue",
          click: () =>
            shell.openExternal("https://github.com/kazuki0422/mindbase/issues"),
        },
      ],
    },
    {
      label: "Settings…",
      click: () => openSettingsWindow(),
    },
    { type: "separator" },
    {
      label: "Quit MindBase Menubar",
      click: () => app.quit(),
    },
  ];
  return Menu.buildFromTemplate(template);
};

const createTray = () => {
  tray = new Tray(templateIcon());
  tray.setToolTip("MindBase Menubar");
  tray.setContextMenu(buildMenu());
};

const refreshHealth = async (manual = false) => {
  const endpoint = `${settings.apiBaseUrl.replace(/\/$/, "")}/health`;
  try {
    const response = await fetch(endpoint);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    state.health = await response.json();
    state.error = null;
    state.lastUpdated = new Date();
  } catch (error) {
    state.health = null;
    state.error = manual ? `Failed (${error.message})` : "Waiting for API…";
  } finally {
    if (tray) {
      tray.setContextMenu(buildMenu());
    }
  }
};

const scheduleRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  refreshTimer = setInterval(refreshHealth, settings.refreshIntervalMs || DEFAULT_REFRESH_MS);
};

const openSettingsWindow = () => {
  if (settingsWindow) {
    settingsWindow.focus();
    return;
  }

  settingsWindow = new BrowserWindow({
    width: 420,
    height: 520,
    title: "MindBase Settings",
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
    },
  });

  settingsWindow.loadFile(path.join(__dirname, "settings.html"));
  settingsWindow.on("closed", () => {
    settingsWindow = null;
  });
};

const registerIpc = () => {
  ipcMain.handle("settings:get", () => settings);
  ipcMain.handle("settings:save", (_event, updated) => {
    persistSettings(updated);
    if (settingsWindow) {
      settingsWindow.webContents.send("settings:updated", settings);
    }
    return settings;
  });
};

const bootstrap = async () => {
  await app.whenReady();
  app.dock?.hide();
  ensureSettings();
  createTray();
  registerIpc();
  await refreshHealth(true);
  scheduleRefresh();
};

app.on("window-all-closed", (event) => {
  event.preventDefault();
});

bootstrap();
