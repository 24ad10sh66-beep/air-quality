import { getHealth, getSummary } from "./api.js";
import { renderLineChart } from "./charts.js";

const pollutantNames = ["PM2.5", "PM10", "NO2", "SO2", "CO"];
const pollutantKeys = ["pm2_5", "pm10", "no2", "so2", "co"];
const $ = (id) => document.getElementById(id);

function setStatus(text, className) {
  const element = $("connection-status");
  element.textContent = text;
  element.className = `status-pill ${className}`;
}

function renderPollutants(values = {}) {
  const list = $("pollutant-list");
  list.replaceChildren();
  pollutantNames.forEach((name, index) => {
    const value = Number(values[pollutantKeys[index]]);
    const row = document.createElement("div");
    row.className = "pollutant-row";
    row.innerHTML = `<span class="pollutant-name">${name}</span><span class="pollutant-track"><span style="width:${Number.isFinite(value) ? Math.min(value, 100) : 0}%"></span></span><strong class="pollutant-value">${Number.isFinite(value) ? value.toFixed(1) : "--"}</strong>`;
    list.append(row);
  });
}

function renderSummary(summary) {
  const aqi = Number(summary.aqi);
  $("aqi-value").textContent = Number.isFinite(aqi) ? Math.round(aqi) : "--";
  $("aqi-label").textContent = summary.aqi_bucket || "No AQI category available";
  $("latest-time").textContent = summary.latest_observation || "--";
  $("aqi-progress").style.width = Number.isFinite(aqi) ? `${Math.min(aqi / 5, 100)}%` : "0";
  $("data-range").textContent = summary.data_range ? `Data range: ${summary.data_range}` : "Data range: --";
  renderPollutants(summary.pollutants);
  renderLineChart($("trend-chart"), summary.trend || []);
  renderLineChart($("forecast-chart"), summary.forecast || [], "#ffb51b");
}

async function refresh(city = "") {
  try {
    await getHealth();
    const summary = await getSummary(city);
    renderSummary(summary);
    $("page-message").hidden = true;
    setStatus("Connected", "status-ok");
  } catch (error) {
    setStatus("API unavailable", "status-error");
    const message = $("page-message");
    message.textContent = "Backend API is not running yet. Dashboard is ready and will show verified data when the API is available.";
    message.hidden = false;
  }
}

$("city-filter").addEventListener("change", (event) => refresh(event.target.value));
renderPollutants();
refresh();
