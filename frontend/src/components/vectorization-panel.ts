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
import { Modal, showParameterModal } from './modal';

const HIDE_VECTORIZE_INSTRUCTIONS_KEY = 'tiitba_hide_vectorize_instructions';

let timemarkPoints: { x: number; y: number }[] = [];
let isPickingTimemarks = false;

// Serializes add/remove/clear point requests so they reach the backend in
// the exact order the user triggered them (see startVectorizing()).
let pointOpQueue: Promise<void> = Promise.resolve();

export function initVectorizationPanel() {
  const btnSetScale = document.getElementById('btn-set-scale') as HTMLButtonElement;
  const btnVectorize = document.getElementById('btn-vectorize') as HTMLButtonElement;
  const btnClear = document.getElementById('btn-clear-points') as HTMLButtonElement;
  const btnPlot = document.getElementById('btn-plot-preview') as HTMLButtonElement;
  const btnExport = document.getElementById('btn-export-ascii') as HTMLButtonElement;
  const pointCount = document.getElementById('point-count')!;
  const scaleStatus = document.getElementById('scale-status');

  // State listener to enable/disable buttons
  state.subscribe(() => {
    const scaleReady = state.hasImage && !!state.ppi;
    if (btnSetScale) {
      btnSetScale.disabled = !scaleReady && !isPickingTimemarks;
      btnSetScale.title = scaleReady
        ? ''
        : state.hasImage ? 'Set a PPI value for this image first' : 'Upload an image first';
    }
    btnVectorize.disabled = !scaleReady;
    btnClear.disabled = state.localPoints.length === 0;
    btnPlot.disabled = state.localPoints.length === 0;
    btnExport.disabled = state.localPoints.length === 0;
    pointCount.textContent = `${state.localPoints.length}`;
  });

  // --- Scale Definition ---
  btnSetScale?.addEventListener('click', () => {
    if (isPickingTimemarks) {
      finishTimemarkPicking();
      return;
    }

    showParameterModal('Define Scale Method', [
      { name: 'method', label: 'Method:', type: 'select', value: 'timemarks', options: [
        { label: 'Time-marks (drum speed)', value: 'timemarks' },
        { label: 'Corner values (absolute)', value: 'corners' }
      ]}
    ], (data) => {
      if (data.method === 'timemarks') {
        startTimemarkPicking();
      } else {
        showCornersModal();
      }
    });
  });

  function showCornersModal() {
    showParameterModal('Set Corner Values', [
      { name: 'leftX', label: 'Left X (time):', type: 'number', value: 0 },
      { name: 'upY', label: 'Top Y (amp):', type: 'number', value: 100 },
      { name: 'rightX', label: 'Right X (time):', type: 'number', value: 3600 },
      { name: 'downY', label: 'Bottom Y (amp):', type: 'number', value: -100 }
    ], async (data) => {
      try {
        await api.setCorners(state.sessionId, data.leftX, data.upY, data.rightX, data.downY);
        state.hasScale = true;
        log(`Corners set: X=[${data.leftX}, ${data.rightX}] Y=[${data.upY}, ${data.downY}]`, 'success', 'vectorization');
        setScaleStatus(`Corners &middot; X=[${data.leftX}, ${data.rightX}] Y=[${data.upY}, ${data.downY}]`);
        state.notify();
      } catch (e: any) { log(`Set corners failed: ${e.message}`, 'error', 'vectorization'); }
    });
  }

  // --- Timemark Picking ---
  function startTimemarkPicking() {
    showCanvasModal();
    isPickingTimemarks = true;
    timemarkPoints = [];
    state.currentMode = 'timemarks';
    state.localPoints.length = 0;
    if (btnSetScale) btnSetScale.textContent = 'Finish Picking';
    log('Click on 3+ time-marks (60s apart). Press Finish when done.', 'info', 'vectorization');

    setPointClickHandler((imgX, imgY) => {
      timemarkPoints.push({ x: imgX, y: imgY });
      state.localPoints.push({ x: imgX, y: imgY });
      refreshOverlay();
      log(`Time-mark ${timemarkPoints.length}: (${imgX}, ${imgY})`, '', 'vectorization');
    });

    state.notify();
  }

  async function finishTimemarkPicking() {
    isPickingTimemarks = false;
    state.currentMode = 'view';
    if (btnSetScale) btnSetScale.textContent = 'Define Scale';

    if (timemarkPoints.length < 3) {
      log('Need at least 3 time-marks', 'error', 'vectorization');
      clearOverlay();
      state.notify();
      return;
    }

    if (!state.ppi) {
      log('Cannot compute drum speed: no PPI set for this image. Set a PPI value first.', 'error', 'vectorization');
      clearOverlay();
      state.notify();
      return;
    }

    try {
      const pts = timemarkPoints.map(p => [p.x, p.y]);
      const result = await api.setTimemarks(state.sessionId, pts, state.ppi);
      state.hasScale = true;
      log(`Drum speed: ${result.drum_speed.toFixed(4)} mm/s`, 'success', 'vectorization');
      log(`Baseline amplitude: ${result.amp0.toFixed(2)} mm`, 'info', 'vectorization');
      setScaleStatus(`Time-marks &middot; Drum speed: ${result.drum_speed.toFixed(4)} mm/s &middot; Baseline: ${result.amp0.toFixed(2)} mm`);
    } catch (e: any) {
      log(`Timemark calculation failed: ${e.message}`, 'error', 'vectorization');
    }

    clearOverlay();
    state.notify();
  }

  function setScaleStatus(text: string) {
    if (scaleStatus) {
      scaleStatus.innerHTML = `<span class="status-dot"></span> ${text}`;
      scaleStatus.classList.remove('hidden');
    }
  }

  // --- Vectorize Mode ---
  btnVectorize.addEventListener('click', () => {
    if (state.isVectorizing) {
      stopVectorizing();
    } else if (localStorage.getItem(HIDE_VECTORIZE_INSTRUCTIONS_KEY) === '1') {
      startVectorizing();
    } else {
      showVectorizeInstructions(startVectorizing);
    }
  });

  function showVectorizeInstructions(onProceed: () => void) {
    const container = document.createElement('div');

    const text = document.createElement('p');
    text.className = 'modal-warning-text';
    text.innerHTML =
      'Click along the trace to mark points, from left to right.<br>' +
      '&bull; Press <strong>Z</strong> to undo the last point.<br>' +
      '&bull; Press <strong>Esc</strong> (or the Stop button) to finish.<br>' +
      'Points are saved to the session as you click.';
    container.appendChild(text);

    const checkGroup = document.createElement('label');
    checkGroup.className = 'modal-checkbox-row';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = 'dontShowAgain';
    checkGroup.appendChild(checkbox);
    checkGroup.appendChild(document.createTextNode("Don't show this again"));
    container.appendChild(checkGroup);

    const modal = new Modal({
      title: 'Vectorizing Instructions',
      content: container,
      confirmText: 'Start Vectorizing',
      cancelText: 'Cancel',
      onConfirm: (data) => {
        if (data.dontShowAgain) localStorage.setItem(HIDE_VECTORIZE_INSTRUCTIONS_KEY, '1');
        onProceed();
      },
    });
    modal.show();
  }

  function startVectorizing() {
    showCanvasModal();
    state.isVectorizing = true;
    state.currentMode = 'vectorize';
    btnVectorize.classList.add('active');
    btnVectorize.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="9" x2="15" y2="15"></line><line x1="15" y1="9" x2="9" y2="15"></line></svg> Stop Vectorizing`;
    log('Click to mark points. Z=undo, Esc=stop', 'info', 'vectorization');

    setPointClickHandler((imgX, imgY) => {
      // Optimistic render
      const optimisticPoint = { x: imgX, y: imgY };
      state.localPoints.push(optimisticPoint);
      refreshOverlay();
      state.notify();

      // Queue the backend call behind any pending point operation so that
      // add/undo requests are applied in the exact order the user triggered
      // them, even if the user clicks or presses undo faster than the
      // network round-trip. Without this, out-of-order responses could make
      // the backend's point list (used for the plot/export) diverge from
      // what is shown on the canvas.
      pointOpQueue = pointOpQueue.then(async () => {
        try {
          const result = await api.addPoint(state.sessionId, imgX, imgY);
          log(`Point ${result.index}: t=${result.time_or_x.toFixed(3)}, a=${result.amplitude_or_y.toFixed(3)}`, '', 'vectorization');
        } catch (e: any) {
          // Revert this specific optimistic point (by reference, since other
          // points may have been added/removed while this call was queued)
          const idx = state.localPoints.indexOf(optimisticPoint);
          if (idx !== -1) state.localPoints.splice(idx, 1);
          refreshOverlay();
          log(`Add point failed: ${e.message}`, 'error', 'vectorization');
        }
        state.notify();
      });
    });

    registerKey('z', () => {
      if (state.localPoints.length === 0) return;
      const removedPoint = state.localPoints[state.localPoints.length - 1];
      removeLastOverlayPoint();
      state.notify();

      pointOpQueue = pointOpQueue.then(async () => {
        try {
          await api.removeLastPoint(state.sessionId);
          log('Undid last point', '', 'vectorization');
        } catch (e: any) {
          // Backend removal failed (or was already out of sync) - restore
          // the point locally so the canvas matches the backend again.
          state.localPoints.push(removedPoint);
          refreshOverlay();
          log(`Undo failed: ${e.message}`, 'error', 'vectorization');
        }
        state.notify();
      });
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
    log(`Vectorization stopped. ${state.localPoints.length} points recorded.`, 'success', 'vectorization');
    state.notify();
  }

  // --- Clear ---
  btnClear.addEventListener('click', () => {
    // Queued behind any pending add/undo so a slow in-flight request can't
    // land after the clear and resurrect a point on the backend.
    pointOpQueue = pointOpQueue.then(async () => {
      try {
        await api.clearPoints(state.sessionId);
        clearOverlay();
        log('All points cleared', '', 'vectorization');
      } catch (e: any) { log(`Clear failed: ${e.message}`, 'error', 'vectorization'); }
      state.notify();
    });
  });

  // --- Plot Preview ---
  btnPlot.addEventListener('click', async () => {
    const plotTabBtn = document.querySelector('.workspace-tab[data-target="plot-view"]') as HTMLButtonElement;
    if (plotTabBtn) plotTabBtn.click();

    try {
      const data = await api.getPlotData(state.sessionId);
      if (!data.time || data.time.length === 0) {
        throw new Error("Received empty data for plotting");
      }
      plotTraces(
        [{ name: 'Vectorized', x: data.time, y: data.amplitude }],
        data.xlabel, data.ylabel,
      );
      log('Plot updated', 'success', 'vectorization');
    } catch (e: any) {
      log(`Plot failed: ${e.message}`, 'error', 'vectorization');
      console.error("Plot error:", e);
    }
  });

  // --- Export ASCII ---
  btnExport.addEventListener('click', () => {
    const url = api.getExportUrl(state.sessionId, 'ascii', 'vectorized');
    window.open(url, '_blank');
    log('Exporting vectorized data as ASCII', 'info', 'vectorization');
  });
}
