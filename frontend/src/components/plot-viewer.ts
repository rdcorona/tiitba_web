/**
 * Plotly.js wrapper for time-series visualization.
 */

// @ts-ignore - plotly loaded via package
import Plotly from 'plotly.js-dist-min';

const containerId = 'plot-container';

export interface Trace {
  name: string;
  x: number[];
  y: number[];
}

export function plotTraces(
  traces: Trace[],
  xlabel = 'Time [s]',
  ylabel = 'Amplitude',
) {
  const plotData = traces.map((t, i) => ({
    x: t.x,
    y: t.y,
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: t.name,
    line: { width: 1 },
  }));

  const layout = {
    margin: { t: 30, r: 20, b: 40, l: 60 },
    xaxis: { title: xlabel, color: '#aaa', gridcolor: '#2a3a5e' },
    yaxis: { title: ylabel, color: '#aaa', gridcolor: '#2a3a5e' },
    paper_bgcolor: '#16213e',
    plot_bgcolor: '#1a1a2e',
    font: { color: '#eee', size: 11 },
    legend: { x: 0, y: 1, bgcolor: 'rgba(0,0,0,0.5)' },
    showlegend: traces.length > 1,
  };

  Plotly.newPlot(containerId, plotData, layout, { responsive: true });
}

export function clearPlot() {
  Plotly.purge(containerId);
}
