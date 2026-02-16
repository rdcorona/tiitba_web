/**
 * Corrections panel: load data, apply corrections, export results.
 */

import * as api from '../api';
import { state } from '../state';
import { log } from './info-log';
import { plotTraces } from './plot-viewer';

export function initCorrectionsPanel() {
  const fileInput = document.getElementById('data-upload') as HTMLInputElement;
  const btnUploadData = document.getElementById('btn-upload-data') as HTMLButtonElement;
  const btnPolarity = document.getElementById('btn-polarity') as HTMLButtonElement;
  const btnDetrend = document.getElementById('btn-detrend') as HTMLButtonElement;
  const btnCurvature = document.getElementById('btn-curvature') as HTMLButtonElement;
  const btnResample = document.getElementById('btn-resample') as HTMLButtonElement;
  const btnWiechert = document.getElementById('btn-wiechert') as HTMLButtonElement;
  const btnExport = document.getElementById('btn-export-corrected') as HTMLButtonElement;

  fileInput.addEventListener('change', () => {
    btnUploadData.disabled = !fileInput.files?.length;
  });

  // --- Upload Data ---
  btnUploadData.addEventListener('click', async () => {
    if (!fileInput.files?.length) return;
    try {
      const result = await api.uploadData(state.sessionId, fileInput.files[0]);
      state.hasData = true;
      enableCorrectionButtons(true);
      log(`Loaded: ${result.filename} (${result.n_samples} samples, t=[${result.time_range[0].toFixed(2)}, ${result.time_range[1].toFixed(2)}])`, 'success');

      // Plot raw data
      const plotData = await api.getDataPlot(state.sessionId, 'raw');
      if (plotData.traces.length > 0) {
        plotTraces(plotData.traces, 'Time [s]', 'Amplitude');
      }
      state.notify();
    } catch (e: any) { log(`Load data failed: ${e.message}`, 'error'); }
  });

  // --- Polarity ---
  btnPolarity.addEventListener('click', async () => {
    try {
      await api.invertPolarity(state.sessionId);
      log('Polarity inverted', 'success');
      await refreshPlot('raw');
    } catch (e: any) { log(`Polarity failed: ${e.message}`, 'error'); }
  });

  // --- Detrend ---
  btnDetrend.addEventListener('click', async () => {
    const window = parseInt((document.getElementById('detrend-window') as HTMLInputElement).value) || 60;
    try {
      await api.detrend(state.sessionId, window);
      log(`Detrended (window=${window}s)`, 'success');
      await refreshPlot('raw,detrend');
    } catch (e: any) { log(`Detrend failed: ${e.message}`, 'error'); }
  });

  // --- Curvature ---
  btnCurvature.addEventListener('click', async () => {
    const speed = parseFloat((document.getElementById('curv-speed') as HTMLInputElement).value);
    const stylet = parseFloat((document.getElementById('curv-stylet') as HTMLInputElement).value);
    const infl = parseFloat((document.getElementById('curv-inflection') as HTMLInputElement).value);
    const sps = parseInt((document.getElementById('curv-sps') as HTMLInputElement).value);
    const spline = (document.getElementById('curv-spline') as HTMLSelectElement).value;

    if ([speed, stylet, infl, sps].some(isNaN)) {
      log('All curvature parameters are required', 'error');
      return;
    }

    try {
      await api.curvatureCorrection(state.sessionId, speed, stylet, infl, sps, spline);
      log(`Curvature corrected + resampled at ${sps} SPS`, 'success');
      await refreshPlot('raw,curvature_ga,curvature_ls');
    } catch (e: any) { log(`Curvature failed: ${e.message}`, 'error'); }
  });

  // --- Resample ---
  btnResample.addEventListener('click', async () => {
    const sps = parseInt((document.getElementById('resample-sps') as HTMLInputElement).value);
    const spline = (document.getElementById('resample-spline') as HTMLSelectElement).value;

    if (isNaN(sps)) { log('SPS is required', 'error'); return; }

    try {
      await api.resampleData(state.sessionId, sps, spline);
      log(`Resampled at ${sps} SPS`, 'success');
      await refreshPlot('raw,resampled');
    } catch (e: any) { log(`Resample failed: ${e.message}`, 'error'); }
  });

  // --- Wiechert ---
  btnWiechert.addEventListener('click', async () => {
    const T0 = parseFloat((document.getElementById('wiechert-t0') as HTMLInputElement).value);
    const epsilon = parseFloat((document.getElementById('wiechert-epsilon') as HTMLInputElement).value);
    const V0 = parseInt((document.getElementById('wiechert-v0') as HTMLInputElement).value);
    const wl = parseFloat((document.getElementById('wiechert-wl') as HTMLInputElement).value);
    const deconv = (document.querySelector('input[name="wiechert-mode"]:checked') as HTMLInputElement).value === 'remove';

    if ([T0, epsilon, V0, wl].some(isNaN)) {
      log('All Wiechert parameters are required', 'error');
      return;
    }

    try {
      await api.wiechertResponse(state.sessionId, T0, epsilon, V0, wl, deconv);
      log(`Wiechert response ${deconv ? 'removed' : 'added'}`, 'success');
      await refreshPlot('raw,response');
    } catch (e: any) { log(`Wiechert failed: ${e.message}`, 'error'); }
  });

  // --- Export ---
  btnExport.addEventListener('click', () => {
    const dataType = (document.getElementById('export-data-type') as HTMLSelectElement).value;
    const format = (document.getElementById('export-format') as HTMLSelectElement).value;
    const url = api.getExportUrl(state.sessionId, format, dataType);
    window.open(url, '_blank');
    log(`Exporting ${dataType} as ${format.toUpperCase()}`, 'info');
  });

  function enableCorrectionButtons(enabled: boolean) {
    btnPolarity.disabled = !enabled;
    btnDetrend.disabled = !enabled;
    btnCurvature.disabled = !enabled;
    btnResample.disabled = !enabled;
    btnWiechert.disabled = !enabled;
    btnExport.disabled = !enabled;
  }
}

async function refreshPlot(series: string) {
  try {
    const plotData = await api.getDataPlot(state.sessionId, series);
    if (plotData.traces.length > 0) {
      plotTraces(plotData.traces, 'Time [s]', 'Amplitude');
    }
  } catch (e: any) {
    log(`Plot refresh failed: ${e.message}`, 'error');
  }
}
