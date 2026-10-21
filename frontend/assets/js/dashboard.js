import { getAnomalies, getForecasts, getHealth, getLiveAqi, getLocationReport, getSummary, searchLocations } from "./api.js";
import { renderLineChart, renderRiskChart } from "./charts.js";

const pollutants = [
  ["PM2.5", "pm2_5", "Fine particulate matter", "µg/m³"],
  ["PM10", "pm10", "Coarse particulate matter", "µg/m³"],
  ["NO", "no_value", "Nitric oxide", "µg/m³"],
  ["NO2", "no2", "Nitrogen dioxide", "µg/m³"],
  ["NOx", "nox", "Nitrogen oxides", "ppb"],
  ["NH3", "nh3", "Ammonia", "µg/m³"],
  ["CO", "co", "Carbon monoxide", "mg/m³"],
  ["SO2", "so2", "Sulfur dioxide", "µg/m³"],
  ["O3", "o3", "Ozone", "µg/m³"],
  ["Benzene", "benzene", "Aromatic hydrocarbon", "µg/m³"],
  ["Toluene", "toluene", "Aromatic hydrocarbon", "µg/m³"],
  ["Xylene", "xylene", "Aromatic hydrocarbon", "µg/m³"],
];
const $ = (id) => document.getElementById(id);
let downloadableReportUrl = null;

function setTheme(theme) {
  const light = theme === "light";
  document.documentElement.dataset.theme = light ? "light" : "dark";
  localStorage.setItem("air-quality-theme", light ? "light" : "dark");
  $("theme-toggle").setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
  $("theme-toggle").querySelector(".theme-icon").textContent = light ? "☾" : "☼";
  $("theme-toggle").querySelector(".theme-label").textContent = light ? "Dark mode" : "Light mode";
}

function renderTrendSummary(points, location) {
  const element = $("trend-summary");
  if (points.length < 2) {
    element.textContent = `${location}: first saved reading recorded. Refresh later to measure the rise or fall.`;
    return;
  }
  const first = Number(points[0].value);
  const latest = Number(points[points.length - 1].value);
  const change = latest - first;
  const direction = change > 0 ? "increased" : change < 0 ? "decreased" : "held steady";
  element.textContent = `${location}: AQI ${direction} by ${Math.abs(Math.round(change))} points (${Math.round(first)} → ${Math.round(latest)}).`;
  element.className = `trend-summary ${change > 0 ? "trend-up" : change < 0 ? "trend-down" : "trend-steady"}`;
}

function setStatus(text, className) {
  const element = $("connection-status");
  element.textContent = text;
  element.className = `status-pill ${className}`;
  $("quick-status").textContent = className === "status-ok" ? "Healthy" : text;
}

function animateNumber(element, target) {
  if (!Number.isFinite(target)) {
    element.textContent = "--";
    return;
  }
  const start = Number(element.dataset.value || 0);
  const started = performance.now();
  const duration = 500;
  const tick = (now) => {
    const progress = Math.min((now - started) / duration, 1);
    const value = start + (target - start) * (1 - Math.pow(1 - progress, 3));
    element.textContent = Math.round(value);
    if (progress < 1) requestAnimationFrame(tick);
    else element.dataset.value = String(target);
  };
  requestAnimationFrame(tick);
}

function renderPollutants(values = {}) {
  const list = $("pollutant-list");
  list.replaceChildren();
  pollutants.forEach(([name, key, description, unit]) => {
    const value = Number(values[key]);
    const row = document.createElement("div");
    row.className = "pollutant-row";
    row.title = `${description}. Reported in ${unit}.`;
    row.innerHTML = `<span class="pollutant-name"><strong>${name}</strong><small>${description}</small></span><span class="pollutant-measure"><span class="pollutant-track"><span style="width:${Number.isFinite(value) ? Math.min(value, 100) : 0}%"></span></span><small class="pollutant-unit">${unit}</small></span><strong class="pollutant-value">${Number.isFinite(value) ? value.toFixed(1) : "--"}</strong>`;
    list.append(row);
  });
}

function renderComparison(previous, live) {
  const previousValue = Number(previous);
  const liveValue = Number(live?.aqi);
  $("previous-aqi").textContent = Number.isFinite(previousValue) && previous !== null ? Math.round(previousValue) : "N/A";
  $("comparison-live-aqi").textContent = Number.isFinite(liveValue) ? Math.round(liveValue) : "--";
  const change = liveValue - previousValue;
  $("aqi-change").textContent = Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${Math.round(change)}` : "--";
  $("aqi-change").className = change > 0 ? "change-up" : change < 0 ? "change-down" : "";
}

function renderForecastSummary(items) {
  const values = items.map((item) => Number(item.prediction ?? item.value)).filter(Number.isFinite);
  const element = $("forecast-summary");
  if (!values.length) {
    element.textContent = "Forecast summary: no model prediction available";
    return;
  }
  const first = values[0];
  const last = values[values.length - 1];
  const direction = last > first + 5 ? "likely to worsen" : last < first - 5 ? "likely to improve" : "likely to remain stable";
  element.textContent = `Next ${values.length} hours: ${Math.round(Math.min(...values))}-${Math.round(Math.max(...values))} AQI; conditions are ${direction}.`;
}

function renderSummary(summary, live = null, forecasts = []) {
  const aqi = Number(summary.aqi);
  document.body.dataset.airLevel = aqi > 200 ? "poor" : aqi > 100 ? "moderate" : "clean";
  animateNumber($("aqi-value"), aqi);
  $("quick-aqi").textContent = Number.isFinite(aqi) ? Math.round(aqi) : "--";
  $("aqi-label").textContent = summary.aqi_bucket || "No AQI category available";
  $("latest-time").textContent = summary.latest_observation ? new Date(summary.latest_observation).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "--";
  if (live) {
    $("latest-time").textContent = live.observed_at ? new Date(live.observed_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "--";
    $("live-source").textContent = live.city
      ? `Live source: OpenWeather · Location: ${live.city}`
      : "Live source: OpenWeather · Location name unavailable";
    renderComparison(summary._historicalAqi, live);
  } else {
    $("live-source").textContent = "Live source unavailable · showing verified historical data";
    renderComparison(summary.aqi, null);
  }
  $("aqi-progress").style.width = Number.isFinite(aqi) ? `${Math.min(aqi / 5, 100)}%` : "0";
  $("data-range").textContent = summary.data_range ? `Data range: ${summary.data_range}` : "Data range: --";
  renderPollutants(summary.pollutants);
  renderLineChart(
    $("trend-chart"),
    summary.trend || [],
    "#36c7ff",
    summary.trendEmptyMessage || "No historical trend data available yet",
  );
  if (!live) {
    renderTrendSummary(summary.trend || [], "Saved location");
  }
  renderLineChart($("forecast-chart"), summary.forecast || [], "#ffb51b");
  renderRiskChart($("risk-chart"), forecasts.length ? forecasts : summary.forecast || []);
  renderForecastSummary(forecasts.length ? forecasts : summary.forecast || []);
  const advice = {
    "Good": "Air quality is satisfactory for most people.",
    "Satisfactory": "Most people can continue normal outdoor activities.",
    "Moderate": "Sensitive people should consider reducing prolonged outdoor exertion.",
    "Poor": "Sensitive groups should limit prolonged outdoor exertion.",
    "Very Poor": "Avoid prolonged outdoor exertion and follow local health guidance.",
    "Severe": "Stay indoors where possible and follow local health guidance.",
  };
  $("advisory-text").textContent = advice[summary.aqi_bucket] ||
    "Guidance is based on the latest verified AQI observation.";
  const bucket = summary.aqi_bucket || "Unavailable";
  $("advisory-title").textContent = `${bucket} air quality`;
  $("advisory-aqi").textContent = `AQI ${Number.isFinite(aqi) ? Math.round(aqi) : "--"}`;
  $("advisory-note").textContent = Number.isFinite(aqi)
    ? "Keep checking conditions before prolonged outdoor activity."
    : "No verified AQI value is available for this selection.";
  $("advisory-mark").className = `advisory-mark advisory-${bucket.toLowerCase().replaceAll(" ", "-")}`;
}

function renderLocationReport(report) {
  const live = report.live;
  const previous = report.history?.[1]?.aqi ?? null;
  const historicalTrend = (report.historical_trend || [])
    .map((item) => ({ label: item.label, value: item.value }))
    .filter((item) => Number.isFinite(Number(item.value)));
  const savedTrend = historicalTrend.length
    ? historicalTrend
    : [...(report.history || [])]
      .reverse()
      .map((item) => ({
        label: item.fetched_at || item.observed_at,
        value: item.aqi,
      }))
      .filter((item) => Number.isFinite(Number(item.value)));
  renderTrendSummary(savedTrend, report.location);
  const summary = {
    aqi: live.aqi,
    aqi_bucket: live.aqi_bucket,
    latest_observation: live.observed_at,
    data_range: null,
    pollutants: live.pollutants,
    trend: savedTrend,
    trendEmptyMessage: savedTrend.length
      ? report.historical_city
        ? `MySQL historical trend: ${report.historical_city}`
        : "MySQL historical trend across stored locations"
      : `No historical readings available for ${report.location}.`,
    forecast: report.forecast.map((item) => ({ label: item.target_time, value: item.prediction })),
    _historicalAqi: previous,
  };
  renderSummary(summary, live, report.forecast);
  $("live-source").textContent = `Live source: OpenWeather · Location: ${report.location}`;
  const previousText = previous == null ? "No earlier saved reading yet" : `Previously saved AQI: ${Math.round(previous)}`;
  $("location-report").textContent = `${report.location}: AQI ${Math.round(live.aqi)} (${live.aqi_bucket}). ${previousText}. ${report.advisory}`;
  $("data-range").textContent = `Coordinates: ${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`;
  const reportUrl = `report.html?lat=${report.latitude}&lon=${report.longitude}&name=${encodeURIComponent(report.location)}`;
  $("location-report-link").href = reportUrl;
  $("location-report-open").href = reportUrl;
  if (downloadableReportUrl) URL.revokeObjectURL(downloadableReportUrl);
  const pollutantLines = Object.entries(live.pollutants)
    .map(([key, value]) => `<li><strong>${key.toUpperCase()}</strong>: ${value == null ? "--" : Number(value).toFixed(1)}</li>`)
    .join("");
  const anomalyLines = report.anomalies.length
    ? report.anomalies.map((item) => `<li>${item.metric}: ${Number(item.value).toFixed(1)} - ${item.reason}</li>`).join("")
    : "<li>No current or forecast anomaly detected.</li>";
  const historyLines = (report.history || []).map((item) => `<li>${new Date(item.fetched_at).toLocaleString()} - AQI ${item.aqi == null ? "--" : Math.round(item.aqi)} (${item.aqi_bucket || "Unavailable"})</li>`).join("") || "<li>No saved history yet.</li>";
  const downloadableHtml = `<!doctype html><html><head><meta charset="utf-8"><title>${report.location} Air Quality Report</title><style>body{font-family:Arial,sans-serif;max-width:760px;margin:40px auto;color:#172b3a}section{border:1px solid #ccd9e2;border-radius:10px;padding:16px;margin:16px 0}li{margin:7px 0}.aqi{font-size:28px;font-weight:700}</style></head><body><h1>${report.location}</h1><p>Live OpenWeather report</p><section><h2>Current condition</h2><p class="aqi">AQI ${Math.round(live.aqi)} - ${live.aqi_bucket}</p><p>${report.advisory}</p></section><section><h2>Previous readings</h2><ul>${historyLines}</ul></section><section><h2>Pollutants</h2><ul>${pollutantLines}</ul></section><section><h2>Potential anomalies</h2><ul>${anomalyLines}</ul></section><section><h2>Forecast</h2><p>${report.forecast.length} live forecast points available.</p></section></body></html>`;
  downloadableReportUrl = URL.createObjectURL(new Blob([downloadableHtml], { type: "text/html" }));
  $("location-report-download").href = downloadableReportUrl;
  renderAnomalies({
    available: report.anomalies.length > 0,
    items: report.anomalies.map((item) => ({
      city: report.location,
      aqi: live.aqi,
      methods: [`${item.metric}: ${Number(item.value).toFixed(1)} (${item.reason})`],
    })),
  });
}

async function searchLocation(event) {
  event.preventDefault();
  const input = $("location-query");
  const query = input.value.trim();
  if (query.length < 2) return;
  const message = $("page-message");
  message.textContent = `Searching live air quality for ${query}...`;
  message.hidden = false;
  try {
    const results = await searchLocations(query);
    if (!results.results.length) throw new Error("Location not found");
    const location = results.results[0];
    const report = await getLocationReport(location.latitude, location.longitude, location.name);
    renderLocationReport(report);
    setStatus("Live location loaded", "status-ok");
    message.hidden = true;
  } catch (error) {
    setStatus("Search failed", "status-error");
    message.textContent = error.message || "Could not load this location.";
  }
}

async function loadCurrentLocation() {
  if (!navigator.geolocation) throw new Error("Browser location is not available");
  const position = await new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: false, timeout: 8000 });
  });
  return getLocationReport(position.coords.latitude, position.coords.longitude, "");
}

function renderAnomalies(response) {
  const content = $("anomaly-content");
  content.replaceChildren();
  $("quick-anomalies").textContent = response.available ? response.items.length : "0";
  if (!response.available) {
    content.innerHTML = "<strong>No anomalies detected</strong><span>No unusual AQI or pollutant level was found for this location.</span>";
    return;
  }
  const latest = response.items.slice(-5).reverse();
  content.innerHTML = `<strong>${response.items.length} potential anomalies</strong><span>${latest.map((item) => `${item.city}: AQI ${Number(item.aqi).toFixed(1)} (${item.methods.join(", ")})`).join("<br>")}</span>`;
}

async function refresh(city = "") {
  const refreshButton = $("refresh-button");
  refreshButton.classList.add("is-loading");
  refreshButton.disabled = true;
  try {
    await getHealth();
    if (!city) {
      try {
        const currentReport = await loadCurrentLocation();
        renderLocationReport(currentReport);
        $("page-message").hidden = true;
        setStatus("Current location loaded", "status-ok");
        return;
      } catch (error) {
        console.warn("Current location unavailable; showing stored data.", error);
      }
    }
    const summary = await getSummary(city);
    const historicalAqi = summary.aqi;
    let live = null;
    try {
      live = await getLiveAqi(city);
      summary.aqi = live.aqi;
      summary.aqi_bucket = live.aqi_bucket;
      summary.latest_observation = live.observed_at;
      summary.pollutants = { ...summary.pollutants, ...live.pollutants };
    } catch (error) {
      console.warn("Live AQI unavailable; showing verified historical data.", error);
    }
    summary._historicalAqi = historicalAqi;
    const forecastResponse = await getForecasts(city);
    const forecasts = forecastResponse.items || [];
    summary.forecast = forecasts.slice(0, 48).map((item) => ({ label: item.target_time, value: item.prediction }));
    const anomalies = await getAnomalies(city);
    renderSummary(summary, live, forecasts.slice(0, 48));
    renderAnomalies(anomalies);
    $("page-message").hidden = true;
    setStatus("Connected", "status-ok");
  } catch (error) {
    setStatus("API unavailable", "status-error");
    const message = $("page-message");
    message.textContent = "Backend API is not running yet. Dashboard is ready and will show verified data when the API is available.";
    message.hidden = false;
  } finally {
    refreshButton.classList.remove("is-loading");
    refreshButton.disabled = false;
  }
}

$("location-search").addEventListener("submit", searchLocation);
$("refresh-button").addEventListener("click", () => refresh());
setTheme(localStorage.getItem("air-quality-theme") || "dark");
$("theme-toggle").addEventListener("click", () => {
  setTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
});
renderPollutants();
refresh();
