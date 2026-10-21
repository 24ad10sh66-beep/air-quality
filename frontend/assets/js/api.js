const API_BASE_URL = window.AIR_QUALITY_API_URL || "http://127.0.0.1:8000";

export async function getSummary(city = "") {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/summary${query}`);
  if (!response.ok) throw new Error(`Summary request failed (${response.status})`);
  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error(`Health request failed (${response.status})`);
  return response.json();
}

export async function getLiveAqi(city = "") {
  let query = "";
  if (navigator.geolocation) {
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
    });
    query = `?lat=${position.coords.latitude}&lon=${position.coords.longitude}`;
  } else if (city) {
    throw new Error("Location permission is required for live AQI");
  } else {
    throw new Error("Location permission is required for live AQI");
  }
  const response = await fetch(`${API_BASE_URL}/api/live-aqi${query}`);
  if (!response.ok) throw new Error(`Live AQI request failed (${response.status})`);
  return response.json();
}

export async function searchLocations(query) {
  const response = await fetch(`${API_BASE_URL}/api/location-search?query=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error(`Location search failed (${response.status})`);
  return response.json();
}

export async function getLocationReport(latitude, longitude, name = "") {
  const query = `?lat=${latitude}&lon=${longitude}&name=${encodeURIComponent(name)}`;
  const response = await fetch(`${API_BASE_URL}/api/location-report${query}`);
  if (!response.ok) throw new Error(`Location report failed (${response.status})`);
  return response.json();
}

export async function getForecasts(city = "") {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/forecasts${query}`);
  if (!response.ok) throw new Error(`Forecast request failed (${response.status})`);
  return response.json();
}

export async function getAnomalies(city = "") {
  const query = city ? `?city=${encodeURIComponent(city)}` : "";
  const response = await fetch(`${API_BASE_URL}/api/anomalies${query}`);
  if (!response.ok) throw new Error(`Anomaly request failed (${response.status})`);
  return response.json();
}
