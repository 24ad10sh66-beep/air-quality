function aqiMeaning(value) {
  if (value <= 50) return ["Good", "Safe for normal outdoor activity.", "good"];
  if (value <= 100) return ["Satisfactory", "Most people can continue normal activity.", "satisfactory"];
  if (value <= 200) return ["Moderate", "Sensitive people should reduce long outdoor activity.", "moderate"];
  if (value <= 300) return ["Poor", "Avoid prolonged outdoor activity if you are sensitive.", "poor"];
  if (value <= 400) return ["Very Poor", "Limit outdoor activity and follow health guidance.", "very-poor"];
  return ["Severe", "Avoid outdoor activity where possible.", "severe"];
}

export function renderLineChart(container, points, color = "#36c7ff", emptyMessage = "No chart data available yet") {
  const svg = container.querySelector("svg");
  const detail = container.parentElement.querySelector(".chart-detail");
  svg.replaceChildren();
  container.removeAttribute("data-empty");
  if (!points?.length) {
    container.dataset.empty = emptyMessage;
    return;
  }

  const width = 620;
  const height = container.classList.contains("compact") ? 180 : 340;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const validPoints = points.filter((point) => Number.isFinite(Number(point.value)));
  if (!validPoints.length) {
    container.dataset.empty = emptyMessage;
    return;
  }
  const values = validPoints.map((point) => Number(point.value));
  const min = Math.min(...values, 0);
  const range = Math.max(Math.max(...values) - min, 1);
  const max = Math.max(...values, 1);
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  const gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
  gradient.setAttribute("id", "chart-fill");
  gradient.setAttribute("x1", "0"); gradient.setAttribute("x2", "0");
  gradient.setAttribute("y1", "0"); gradient.setAttribute("y2", "1");
  const topStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
  topStop.setAttribute("offset", "0%"); topStop.setAttribute("stop-color", color); topStop.setAttribute("stop-opacity", ".35");
  const bottomStop = document.createElementNS("http://www.w3.org/2000/svg", "stop");
  bottomStop.setAttribute("offset", "100%"); bottomStop.setAttribute("stop-color", color); bottomStop.setAttribute("stop-opacity", "0");
  gradient.append(topStop, bottomStop); defs.append(gradient); svg.append(defs);
  const x = (index) => 18 + (index / Math.max(validPoints.length - 1, 1)) * (width - 36);
  const y = (value) => height - 24 - ((value - min) / range) * (height - 48);
  for (let index = 1; index < 5; index += 1) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", "18"); line.setAttribute("x2", String(width - 18));
    line.setAttribute("y1", String(18 + index * ((height - 42) / 5))); line.setAttribute("y2", String(18 + index * ((height - 42) / 5)));
    line.setAttribute("class", "chart-gridline"); svg.append(line);
  }
  const path = validPoints.map((point, index) => `${index ? "L" : "M"} ${x(index)} ${y(Number(point.value))}`).join(" ");
  if (validPoints.length > 1) {
    const area = document.createElementNS("http://www.w3.org/2000/svg", "path");
    area.setAttribute("d", `${path} L ${x(validPoints.length - 1)} ${height - 24} L ${x(0)} ${height - 24} Z`);
    area.setAttribute("class", "chart-area");
    svg.append(area);
  }
  const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
  line.setAttribute("d", path); line.setAttribute("class", "chart-line"); line.style.stroke = color; svg.append(line);
  validPoints.forEach((point, index) => {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(x(index))); dot.setAttribute("cy", String(y(Number(point.value))));
    dot.setAttribute("r", "4"); dot.setAttribute("class", "chart-dot"); svg.append(dot);
    const tooltip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    const label = point.label ? new Date(point.label).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Point";
    tooltip.textContent = `${label}: ${Number(point.value).toFixed(1)} AQI`;
    dot.append(tooltip);
    dot.setAttribute("tabindex", "0");
    const showDetail = () => {
      const value = Number(point.value);
      const [category, advice, className] = aqiMeaning(value);
      detail.className = `chart-detail ${className}`;
      detail.replaceChildren();
      const labelElement = document.createElement("span");
      labelElement.className = "detail-label";
      labelElement.textContent = point.label ? new Date(point.label).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Selected point";
      const valueElement = document.createElement("strong");
      valueElement.textContent = `${value.toFixed(1)} AQI · ${category}`;
      const adviceElement = document.createElement("span");
      adviceElement.textContent = advice;
      detail.append(labelElement, valueElement, adviceElement);
    };
    dot.addEventListener("click", showDetail);
    dot.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        showDetail();
      }
    });
  });
}

export function renderRiskChart(container, points) {
  container.replaceChildren();
  const validPoints = points.map((point) => ({
    ...point,
    value: point.value ?? point.prediction,
  })).filter((point) => Number.isFinite(Number(point.value)));
  if (!validPoints.length) {
    container.dataset.empty = "No forecast zones available";
    return;
  }
  delete container.dataset.empty;
  validPoints.forEach((point) => {
    const value = Number(point.value);
    const zone = value <= 50 ? "good" : value <= 100 ? "satisfactory" : value <= 200 ? "moderate" : value <= 300 ? "poor" : value <= 400 ? "very-poor" : "severe";
    const bar = document.createElement("span");
    bar.className = `risk-segment risk-${zone}`;
    bar.title = `${point.label ? new Date(point.label).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Forecast"}: AQI ${Math.round(value)} · ${zone.replace("-", " ")}`;
    container.append(bar);
  });
}
