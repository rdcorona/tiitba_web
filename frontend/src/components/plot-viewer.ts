/**
 * Plotly.js wrapper for time-series visualization.
 */

// @ts-ignore
import * as Plotly from 'plotly.js-dist-min';

const containerId = 'plot-container';

export interface Trace {
  name: string;
  x: number[];
  y: number[];
}

let lastTraces: Trace[] | null = null;
let lastXLabel = '';
let lastYLabel = '';

export function plotTraces(
  traces: Trace[],
  xlabel = 'Time [s]',
  ylabel = 'Amplitude',
) {
  lastTraces = traces;
  lastXLabel = xlabel;
  lastYLabel = ylabel;

  const isLight = document.documentElement.getAttribute('data-theme') === 'light';

  // Light theme colors: light gray, greens, blues (Plot uses blue and greens)
  // Dark theme colors: blue, green, red
  const traceColorsDark = ['#e94560', '#4caf50', '#64b5f6'];
  const traceColorsLight = ['#0277bd', '#2e7d32', '#f57c00'];

  const colors = isLight ? traceColorsLight : traceColorsDark;

  const plotData = traces.map((t, i) => ({
    x: t.x,
    y: t.y,
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: t.name,
    line: { width: 1, color: colors[i % colors.length] },
  }));

  const layout = {
    margin: { t: 30, r: 20, b: 40, l: 60 },
    xaxis: { 
      title: xlabel, 
      color: isLight ? '#4a5568' : '#aaa', 
      gridcolor: isLight ? '#cbd5e1' : '#2a3a5e', 
      autorange: true, 
      zeroline: false 
    },
    yaxis: { 
      title: ylabel, 
      color: isLight ? '#4a5568' : '#aaa', 
      gridcolor: isLight ? '#cbd5e1' : '#2a3a5e', 
      autorange: true, 
      zeroline: false 
    },
    paper_bgcolor: isLight ? '#ffffff' : '#16213e',
    plot_bgcolor: isLight ? '#f0f4f8' : '#1a1a2e',
    font: { color: isLight ? '#1a202c' : '#eee', size: 11 },
    legend: { x: 0, y: 1, bgcolor: isLight ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.5)' },
    showlegend: traces.length > 1,
  };

  Plotly.react(containerId, plotData, layout, { responsive: true });
}

export function clearPlot() {
  lastTraces = null;
  Plotly.purge(containerId);
}

// Re-plot when theme changes
window.addEventListener('themeChanged', () => {
  if (lastTraces) {
    plotTraces(lastTraces, lastXLabel, lastYLabel);
  }
});
