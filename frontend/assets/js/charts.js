export function renderLineChart(container, points, color = "#36c7ff") {
  const svg = container.querySelector("svg");
  svg.replaceChildren();
  container.removeAttribute("data-empty");
  if (!points?.length) {
    container.dataset.empty = "No chart data available yet";
    return;
  }
  const width = 620;
  const height = 220;
  const values = points.map((point) => Number(point.value));
  const max = Math.max(...values, 1);
  const x = (index) => 18 + (index / Math.max(points.length - 1, 1)) * (width - 36);
  const y = (value) => height - 24 - (value / max) * (height - 48);
  for (let index = 1; index < 5; index += 1) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", "18"); line.setAttribute("x2", String(width - 18));
    line.setAttribute("y1", String(index * 42)); line.setAttribute("y2", String(index * 42));
    line.setAttribute("class", "chart-gridline"); svg.append(line);
  }
  const path = points.map((point, index) => `${index ? "L" : "M"} ${x(index)} ${y(Number(point.value))}`).join(" ");
  const line = document.createElementNS("http://www.w3.org/2000/svg", "path");
  line.setAttribute("d", path); line.setAttribute("class", "chart-line"); line.style.stroke = color; svg.append(line);
  points.forEach((point, index) => {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(x(index))); dot.setAttribute("cy", String(y(Number(point.value))));
    dot.setAttribute("r", "4"); dot.setAttribute("class", "chart-dot"); svg.append(dot);
  });
}
