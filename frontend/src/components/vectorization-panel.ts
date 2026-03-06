/**
 * Vectorization panel: scale definition, point digitization, plot, export.
 */

import * as api from '../api';
import { state } from '../state';
import { log } from './info-log';
import {
  setPointClickHandler, clearOverlay, refreshOverlay,
  removeLastOverlayPoint, showCanvasModal
} from './canvas-viewer';
import { plotTraces } from './plot-viewer';
import { registerKey, unregisterKey } from '../utils/keyboard';

let timemarkPoints: { x: number; y: number }[] = [];
let isPickingTimemarks = false;

export function initVectorizationPanel() {
  const btnPickTm = document.getElementById('btn-pick-timemarks') as HTMLButtonElement;
  const btnSetCorners = document.getElementById('btn-set-corners') as HTMLButtonElement;
  const btnVectorize = document.getElementById('btn-vectorize') as HTMLButtonElement;
  const btnShowCanvasVec = document.getElementById('btn-show-canvas-vec') as HTMLButtonElement;
  const btnClear = document.getElementById('btn-clear-points') as HTMLButtonElement;
  const btnPlot = document.getElementById('btn-plot-preview') as HTMLButtonElement;
  const btnExport = document.getElementById('btn-export-ascii') as HTMLButtonElement;
  const cornerInputs = document.getElementById('corner-inputs')!;
  const pointCount = document.getElementById('point-count')!;

  // Scale method radio
  document.querySelectorAll('input[name="scale-method"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      const val = (e.target as HTMLInputElement).value;
      cornerInputs.classList.toggle('hidden', val !== 'corners');
      btnPickTm.classList.toggle('hidden', val !== 'timemarks');
    });
  });

  // State listener to enable/disable buttons
  state.subscribe(() => {
    btnPickTm.disabled = !state.hasImage;
    btnVectorize.disabled = !state.hasImage;
    btnClear.disabled = state.localPoints.length === 0;
    btnPlot.disabled = state.localPoints.length === 0;
    btnExport.disabled = state.localPoints.length === 0;
    pointCount.textContent = `${state.localPoints.length} points`;
    if (state.hasImage) {
      btnShowCanvasVec.classList.remove('hidden');
    }
  });

  btnShowCanvasVec.addEventListener('click', showCanvasModal);

  // --- Timemark Picking ---
  btnPickTm.addEventListener('click', () => {
    showCanvasModal();
    if (isPickingTimemarks) {
      finishTimemarkPicking();
      return;
    }
    isPickingTimemarks = true;
    timemarkPoints = [];
    state.currentMode = 'timemarks';
    state.localPoints = [];
    btnPickTm.textContent = 'Finish Picking';
    log('Click on 3+ time-marks (60s apart). Press Finish when done.', 'info');

    setPointClickHandler((imgX, imgY) => {
      timemarkPoints.push({ x: imgX, y: imgY });
      state.localPoints.push({ x: imgX, y: imgY });
      refreshOverlay();
      log(`Time-mark ${timemarkPoints.length}: (${imgX}, ${imgY})`, '');
    });

    state.notify();
  });

  async function finishTimemarkPicking() {
    isPickingTimemarks = false;
    state.currentMode = 'view';
    btnPickTm.textContent = 'Pick Time-marks';

    if (timemarkPoints.length < 3) {
      log('Need at least 3 time-marks', 'error');
      clearOverlay();
      state.notify();
      return;
    }

    try {
      const pts = timemarkPoints.map(p => [p.x, p.y]);
      const ppi = state.ppi || 600;
      const result = await api.setTimemarks(state.sessionId, pts, ppi);
      state.hasScale = true;
      log(`Drum speed: ${result.drum_speed.toFixed(4)} mm/s`, 'success');
      log(`Baseline amplitude: ${result.amp0.toFixed(2)} mm`, 'info');
    } catch (e: any) {
      log(`Timemark calculation failed: ${e.message}`, 'error');
    }

    clearOverlay();
    state.notify();
  }

  // --- Corner Values ---
  btnSetCorners.addEventListener('click', async () => {
    showCanvasModal();
    const leftX = parseFloat((document.getElementById('corner-left-x') as HTMLInputElement).value);
    const upY = parseFloat((document.getElementById('corner-up-y') as HTMLInputElement).value);
    const rightX = parseFloat((document.getElementById('corner-right-x') as HTMLInputElement).value);
    const downY = parseFloat((document.getElementById('corner-down-y') as HTMLInputElement).value);

    if ([leftX, upY, rightX, downY].some(isNaN)) {
      log('All corner values are required', 'error');
      return;
    }

    try {
      await api.setCorners(state.sessionId, leftX, upY, rightX, downY);
      state.hasScale = true;
      log(`Corners set: X=[${leftX}, ${rightX}] Y=[${upY}, ${downY}]`, 'success');
      state.notify();
    } catch (e: any) {
      log(`Set corners failed: ${e.message}`, 'error');
    }
  });

  // --- Vectorize Mode ---
  btnVectorize.addEventListener('click', () => {
    if (state.isVectorizing) {
      stopVectorizing();
    } else {
      startVectorizing();
    }
  });

  function startVectorizing() {
    showCanvasModal();
    state.isVectorizing = true;
    state.currentMode = 'vectorize';
    btnVectorize.textContent = 'Stop Vectorizing';
    log('Click to mark points. Z=undo, Esc=stop', 'info');

    setPointClickHandler(async (imgX, imgY) => {
      // Optimistic render
      state.localPoints.push({ x: imgX, y: imgY });
      refreshOverlay();

      try {
        const result = await api.addPoint(state.sessionId, imgX, imgY);
        log(`Point ${result.index}: t=${result.time_or_x.toFixed(3)}, a=${result.amplitude_or_y.toFixed(3)}`, '');
        pointCount.textContent = `${state.localPoints.length} points`;
      } catch (e: any) {
        // Revert optimistic add
        state.localPoints.pop();
        refreshOverlay();
        log(`Add point failed: ${e.message}`, 'error');
      }
      state.notify();
    });

    registerKey('z', async () => {
      if (state.localPoints.length === 0) return;
      removeLastOverlayPoint();
      try {
        await api.removeLastPoint(state.sessionId);
        log('Undid last point', '');
      } catch (e: any) { log(`Undo failed: ${e.message}`, 'error'); }
      state.notify();
    });

    registerKey('escape', () => stopVectorizing());
    state.notify();
  }

  function stopVectorizing() {
    state.isVectorizing = false;
    state.currentMode = 'view';
    btnVectorize.textContent = 'Start Vectorizing';
    setPointClickHandler(() => {});
    unregisterKey('z');
    unregisterKey('escape');
    log(`Vectorization stopped. ${state.localPoints.length} points recorded.`, 'success');
    state.notify();
  }

  // --- Clear ---
  btnClear.addEventListener('click', async () => {
    try {
      await api.clearPoints(state.sessionId);
      clearOverlay();
      log('All points cleared', '');
      state.notify();
    } catch (e: any) { log(`Clear failed: ${e.message}`, 'error'); }
  });

  // --- Plot Preview ---
  btnPlot.addEventListener('click', async () => {
    document.getElementById('canvas-modal')?.classList.add('hidden');
    try {
      const data = await api.getPlotData(state.sessionId);
      if (!data.time || data.time.length === 0) {
        throw new Error("Received empty data for plotting");
      }
      plotTraces(
        [{ name: 'Vectorized', x: data.time, y: data.amplitude }],
        data.xlabel, data.ylabel,
      );
      log('Plot updated', 'success');
    } catch (e: any) { 
      log(`Plot failed: ${e.message}`, 'error'); 
      console.error("Plot error:", e);
    }
  });

  // --- Export ASCII ---
  btnExport.addEventListener('click', () => {
    const url = api.getExportUrl(state.sessionId, 'ascii', 'vectorized');
    window.open(url, '_blank');
    log('Exporting vectorized data as ASCII', 'info');
  });
}
