/**
 * Corrections panel: detrend, curvature, resample, response, export.
 */

import * as api from '../api';
import { state } from '../state';
import { log } from './info-log';
import { plotTraces } from './plot-viewer';
import { Modal, showParameterModal } from './modal';

export function initCorrectionsPanel() {
  const fileInput = document.getElementById('data-upload') as HTMLInputElement;
  const btnUpload = document.getElementById('btn-upload-data') as HTMLButtonElement;
  const btnPolarity = document.getElementById('btn-polarity') as HTMLButtonElement;
  const btnDetrend = document.getElementById('btn-detrend') as HTMLButtonElement;
  const btnCurvature = document.getElementById('btn-curvature') as HTMLButtonElement;
  const btnResample = document.getElementById('btn-resample') as HTMLButtonElement;
  const btnWiechert = document.getElementById('btn-wiechert') as HTMLButtonElement;
  const btnExport = document.getElementById('btn-export-corrected') as HTMLButtonElement;
  const exportType = document.getElementById('export-data-type') as HTMLSelectElement;
  const exportFormat = document.getElementById('export-format') as HTMLSelectElement;
  const dropZone = document.getElementById('data-drop-zone');

  // Handle Drag and Drop
  if (dropZone) {
      dropZone.addEventListener('dragover', (e) => {
          e.preventDefault();
          dropZone.classList.add('drag-over');
      });
      dropZone.addEventListener('dragleave', () => {
          dropZone.classList.remove('drag-over');
      });
      dropZone.addEventListener('drop', (e) => {
          e.preventDefault();
          dropZone.classList.remove('drag-over');
          if (e.dataTransfer?.files.length) {
              handleUpload(e.dataTransfer.files[0]);
          }
      });
  }

  fileInput.addEventListener('change', () => {
      if (fileInput.files?.length) {
          handleUpload(fileInput.files[0]);
      }
  });

  async function handleUpload(file: File) {
    try {
      log('Uploading data...', 'info');
      const result = await api.uploadData(state.sessionId, file);
      state.hasData = true;
      log(`Data loaded: ${result.filename} (${result.n_samples} samples)`, 'success');
      refreshPlot();
      state.notify();
    } catch (e: any) { log(`Upload failed: ${e.message}`, 'error'); }
  }

  btnUpload.addEventListener('click', () => fileInput.click());

  state.subscribe(() => {
    const hasData = state.hasData;
    btnPolarity.disabled = !hasData;
    btnDetrend.disabled = !hasData;
    btnCurvature.disabled = !hasData;
    btnResample.disabled = !hasData;
    btnWiechert.disabled = !hasData;
    btnExport.disabled = !hasData;
  });

  btnPolarity.addEventListener('click', async () => {
    try {
      await api.invertPolarity(state.sessionId);
      log('Polarity inverted', 'success');
      refreshPlot();
    } catch (e: any) { log(`Operation failed: ${e.message}`, 'error'); }
  });

  btnDetrend.addEventListener('click', () => {
    showParameterModal('Detrending Parameters', [
      { name: 'window_size', label: 'Window Size (samples):', type: 'number', value: 60, min: 1 }
    ], async (data) => {
      try {
        await api.detrend(state.sessionId, data.window_size);
        log('Detrending applied', 'success');
        refreshPlot();
      } catch (e: any) { log(`Detrend failed: ${e.message}`, 'error'); }
    });
  });

  btnCurvature.addEventListener('click', () => {
    showParameterModal('Curvature Correction (G&A94)', [
      { name: 'drum_speed', label: 'Drum Speed (mm/s):', type: 'number', value: state.ppi ? 0.25 : 0.25, step: 0.001 },
      { name: 'stylet_length', label: 'Stylet Length (mm):', type: 'number', value: 120, step: 1 },
      { name: 'inflection_amp', label: 'Inflection Amplitude:', type: 'number', value: 0, step: 0.1 },
      { name: 'sps', label: 'Target SPS:', type: 'number', value: 100, min: 1 },
      { name: 'spline_order', label: 'Spline Order:', type: 'select', value: 'cubic', options: [
        { label: 'Linear', value: 'slinear' },
        { label: 'Quadratic', value: 'quadratic' },
        { label: 'Cubic', value: 'cubic' }
      ]}
    ], async (data) => {
      try {
        await api.curvatureCorrection(
          state.sessionId, data.drum_speed, data.stylet_length,
          data.inflection_amp, data.sps, data.spline_order
        );
        log('Curvature correction applied', 'success');
        refreshPlot();
      } catch (e: any) { log(`Curvature failed: ${e.message}`, 'error'); }
    });
  });

  btnResample.addEventListener('click', () => {
    showParameterModal('Resampling Parameters', [
      { name: 'sps', label: 'Target SPS:', type: 'number', value: 100, min: 1 },
      { name: 'spline_order', label: 'Spline Order:', type: 'select', value: 'cubic', options: [
        { label: 'Linear', value: 'slinear' },
        { label: 'Quadratic', value: 'quadratic' },
        { label: 'Cubic', value: 'cubic' }
      ]}
    ], async (data) => {
      try {
        await api.resampleData(state.sessionId, data.sps, data.spline_order);
        log('Resampling applied', 'success');
        refreshPlot();
      } catch (e: any) { log(`Resample failed: ${e.message}`, 'error'); }
    });
  });

  btnWiechert.addEventListener('click', () => {
    showParameterModal('Wiechert Response Correction', [
      { name: 't0', label: 'Natural Period T0 (s):', type: 'number', value: 12, step: 0.1 },
      { name: 'epsilon', label: 'Damping Ratio \u03B5:', type: 'number', value: 4, step: 0.1 },
      { name: 'v0', label: 'Magnification V0:', type: 'number', value: 160, step: 1 },
      { name: 'wl', label: 'Water Level:', type: 'number', value: 0.01, step: 0.001, min: 0, max: 1 },
      { name: 'mode', label: 'Mode:', type: 'select', value: 'remove', options: [
        { label: 'Remove Response (Deconvolve)', value: 'remove' },
        { label: 'Add Response (Convolve)', value: 'add' }
      ]}
    ], async (data) => {
      try {
        await api.wiechertResponse(
          state.sessionId, data.t0, data.epsilon,
          data.v0, data.wl, data.mode === 'remove'
        );
        log('Wiechert response applied', 'success');
        refreshPlot();
      } catch (e: any) { log(`Wiechert failed: ${e.message}`, 'error'); }
    });
  });

  btnExport.addEventListener('click', () => {
    const format = exportFormat.value;
    const type = exportType.value;

    if (format === 'sac' || format === 'miniseed') {
      showExportMetadataModal(format, (metadata) => {
        const url = api.getExportUrl(state.sessionId, format, type, metadata);
        window.open(url, '_blank');
        log(`Exporting ${type} as ${format.toUpperCase()}`, 'info');
      });
    } else {
      const url = api.getExportUrl(state.sessionId, format, type);
      window.open(url, '_blank');
      log(`Exporting ${type} as ${format.toUpperCase()}`, 'info');
    }
  });

  async function refreshPlot() {
    try {
      const data = await api.getDataPlot(state.sessionId, 'raw,detrend,resampled,response');
      const plotTabBtn = document.querySelector('.workspace-tab[data-target="plot-view"]') as HTMLButtonElement;
      if (plotTabBtn) plotTabBtn.click();
      plotTraces(data.traces, 'Time (s)', 'Amplitude');
    } catch (e: any) { log(`Plot failed: ${e.message}`, 'error'); }
  }
}

function showExportMetadataModal(format: 'sac' | 'miniseed', onConfirm: (data: any) => void) {
  // MiniSEED can hold multiple components, so it gets a separate component field
  // that is combined with the channel code. SAC is single-trace, so one channel
  // field (e.g. "HHZ") is enough.
  const fields: any[] = [
    { name: 'station', label: 'Station Code:', type: 'text', value: 'STA' },
    { name: 'network', label: 'Network Code:', type: 'text', value: 'XX' },
  ];

  if (format === 'miniseed') {
    fields.push(
      { name: 'channel', label: 'Channel Code (e.g., HH):', type: 'text', value: 'HH' },
      { name: 'component', label: 'Component (Z, N, E):', type: 'text', value: 'Z' },
    );
  } else {
    fields.push({ name: 'channel', label: 'Channel (e.g., HHZ):', type: 'text', value: 'HHZ' });
  }

  fields.push({
    name: 'starttime', label: 'Start Time (YYYY-MM-DD HH:MM:SS):', type: 'text',
    value: new Date().toISOString().replace('T', ' ').split('.')[0],
  });

  showParameterModal(`Export Metadata (${format.toUpperCase()})`, fields, (data) => {
    if (format === 'miniseed') {
      data.channel = `${data.channel}${data.component}`;
      delete data.component;
    }
    onConfirm(data);
  });
}
