/**
 * Dibuja un gauge semicircular tipo panel de control (SCADA) dentro de un
 * <svg id="..."> viewBox="0 0 260 160". La aguja marca el valor de MAPE
 * actual; el arco cambia de color según su posición respecto al umbral.
 */
function drawGauge(svgId, value, threshold) {
  const svg = document.getElementById(svgId);
  if (!svg) return;

  const cx = 130, cy = 140, r = 100;
  // Escala del gauge: de 0 a 2.2x el umbral (o mínimo 20%) para dar contexto
  const maxScale = Math.max(threshold * 2.2, 20);
  const clampedValue = Math.min(value, maxScale);

  const startAngle = 180; // grados, izquierda
  const endAngle = 0;     // derecha

  function angleForValue(v) {
    const frac = v / maxScale;
    return startAngle - frac * (startAngle - endAngle);
  }

  function polarToXY(angleDeg, radius) {
    const rad = (angleDeg * Math.PI) / 180;
    return [cx + radius * Math.cos(rad), cy - radius * Math.sin(rad)];
  }

  function arcPath(a1, a2, radius) {
    const [x1, y1] = polarToXY(a1, radius);
    const [x2, y2] = polarToXY(a2, radius);
    const largeArc = Math.abs(a1 - a2) > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
  }

  const ns = "http://www.w3.org/2000/svg";
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  // Zonas de color: verde (bueno) hasta el umbral, ámbar hasta 1.5x umbral, rojo el resto
  const zoneGoodEnd = Math.min(threshold, maxScale);
  const zoneWarnEnd = Math.min(threshold * 1.5, maxScale);

  const zones = [
    { from: 0, to: zoneGoodEnd, color: "#2FD3B0" },
    { from: zoneGoodEnd, to: zoneWarnEnd, color: "#F2A93B" },
    { from: zoneWarnEnd, to: maxScale, color: "#E5484D" }
  ];

  zones.forEach((z) => {
    if (z.to <= z.from) return;
    const a1 = angleForValue(z.from);
    const a2 = angleForValue(z.to);
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", arcPath(a1, a2, r));
    path.setAttribute("stroke", z.color);
    path.setAttribute("stroke-width", "16");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke-linecap", "butt");
    path.setAttribute("opacity", "0.85");
    svg.appendChild(path);
  });

  // Marca de umbral
  const tAngle = angleForValue(Math.min(threshold, maxScale));
  const [tx1, ty1] = polarToXY(tAngle, r - 12);
  const [tx2, ty2] = polarToXY(tAngle, r + 12);
  const tickLine = document.createElementNS(ns, "line");
  tickLine.setAttribute("x1", tx1);
  tickLine.setAttribute("y1", ty1);
  tickLine.setAttribute("x2", tx2);
  tickLine.setAttribute("y2", ty2);
  tickLine.setAttribute("stroke", "#E6EDF5");
  tickLine.setAttribute("stroke-width", "2.5");
  svg.appendChild(tickLine);

  // Aguja
  const needleAngle = angleForValue(clampedValue);
  const [nx, ny] = polarToXY(needleAngle, r - 20);
  const needle = document.createElementNS(ns, "line");
  needle.setAttribute("x1", cx);
  needle.setAttribute("y1", cy);
  needle.setAttribute("x2", nx);
  needle.setAttribute("y2", ny);
  needle.setAttribute("stroke", "#E6EDF5");
  needle.setAttribute("stroke-width", "3");
  needle.setAttribute("stroke-linecap", "round");
  svg.appendChild(needle);

  const hub = document.createElementNS(ns, "circle");
  hub.setAttribute("cx", cx);
  hub.setAttribute("cy", cy);
  hub.setAttribute("r", "6");
  hub.setAttribute("fill", "#E6EDF5");
  svg.appendChild(hub);

  // Etiquetas de escala (0 y max)
  const label0 = document.createElementNS(ns, "text");
  label0.setAttribute("x", cx - r);
  label0.setAttribute("y", cy + 20);
  label0.setAttribute("fill", "#8A99B3");
  label0.setAttribute("font-size", "11");
  label0.setAttribute("font-family", "JetBrains Mono, monospace");
  label0.textContent = "0%";
  svg.appendChild(label0);

  const labelMax = document.createElementNS(ns, "text");
  labelMax.setAttribute("x", cx + r - 24);
  labelMax.setAttribute("y", cy + 20);
  labelMax.setAttribute("fill", "#8A99B3");
  labelMax.setAttribute("font-size", "11");
  labelMax.setAttribute("font-family", "JetBrains Mono, monospace");
  labelMax.textContent = maxScale.toFixed(0) + "%";
  svg.appendChild(labelMax);
}
