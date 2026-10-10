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
