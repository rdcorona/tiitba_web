/**
 * Image processing panel: upload, rotate, contrast, binarize, trim.
 */

import * as api from '../api';
import { state } from '../state';
import { log } from './info-log';
import { loadImage, setTrimCompleteHandler, clearOverlay, showCanvasModal } from './canvas-viewer';
import { Modal, showParameterModal } from './modal';

export function initImagePanel() {
  const fileInput = document.getElementById('image-upload') as HTMLInputElement;
  const ppiInput = document.getElementById('ppi-input') as HTMLInputElement;
  const btnRotate = document.getElementById('btn-rotate') as HTMLButtonElement;
  const btnContrast = document.getElementById('btn-contrast') as HTMLButtonElement;
  const btnBinarize = document.getElementById('btn-binarize') as HTMLButtonElement;
  const btnUndoBinarize = document.getElementById('btn-undo-binarize') as HTMLButtonElement;
  const btnTrim = document.getElementById('btn-trim-mode') as HTMLButtonElement;
  const imageInfo = document.getElementById('image-info')!;
  const dropZone = document.getElementById('image-drop-zone');

  // Handle file selection via input
  fileInput.addEventListener('change', async () => {
    if (fileInput.files?.length) {
        handleUpload(fileInput.files[0]);
    }
  });

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

  async function handleUpload(file: File) {
    const ppi = ppiInput.value ? parseFloat(ppiInput.value) : undefined;

    try {
      log('Uploading image...', 'info');
      const result = await api.uploadImage(state.sessionId, file, ppi);

      state.hasImage = true;
      state.imageWidth = result.width;
      state.imageHeight = result.height;
      state.ppi = result.ppi;
      ppiInput.value = result.ppi ? String(result.ppi) : '';
      setUploadLabelLoaded();
      updateWorkspaceFilename(result.filename);

      if (result.ppi_required) {
        log('PPI could not be auto-detected from the image metadata', 'info');
        showPPIRequiredModal(async (newPpi) => {
          const update = await api.updatePPI(state.sessionId, newPpi);
          state.ppi = update.ppi;
          ppiInput.value = String(update.ppi);
          log(`PPI set to ${update.ppi}`, 'success');
          updateImageInfo(result.width, result.height, update.width_mm, update.height_mm, update.ppi);
          reloadImage();
          state.notify();
        });
      } else {
        log(`Image uploaded: ${result.filename} (${result.width}x${result.height})`, 'success');
        updateImageInfo(result.width, result.height, result.width_mm, result.height_mm, result.ppi);
        reloadImage();
      }

      state.notify();
      showCanvasModal();
    } catch (e: any) {
        log(`Upload failed: ${e.message}`, 'error');
    }
  }

  function updateImageInfo(w: number, h: number, w_mm: number | null | undefined, h_mm: number | null | undefined, ppi: number | null) {
    if (w_mm) {
      imageInfo.textContent = `${w}x${h} px | ${w_mm.toFixed(1)}x${h_mm?.toFixed(1)} mm | PPI: ${ppi}`;
    } else {
      imageInfo.textContent = `${w}x${h} px | PPI: ${ppi ?? 'unknown'}`;
    }
  }

  btnRotate.addEventListener('click', async () => {
    try {
      const result = await api.rotateImage(state.sessionId);
      await reloadImage();
      log(`Rotated 90deg CW (${result.width}x${result.height})`, 'success');
    } catch (e: any) { log(`Rotate failed: ${e.message}`, 'error'); }
  });

  btnContrast.addEventListener('click', () => {
    showParameterModal('Contrast Enhancement (CLAHE)', [
      { name: 'clip_limit', label: 'Clip Limit', type: 'number', value: 2.2, step: 0.1 },
      { name: 'tile_size', label: 'Tile Grid Size', type: 'number', value: 8, step: 1 }
    ], async (data) => {
      try {
        await api.enhanceContrast(state.sessionId, data.clip_limit, data.tile_size);
        await reloadImage();
        log('CLAHE contrast enhancement applied', 'success');
      } catch (e: any) { log(`Contrast failed: ${e.message}`, 'error'); }
    });
  });

  btnBinarize.addEventListener('click', async () => {
    try {
      const result = await api.binarizeImage(state.sessionId);
      await reloadImage();
      btnBinarize.classList.add('hidden');
      btnUndoBinarize.classList.remove('hidden');
      log(`Binarized (Otsu threshold: ${result.threshold.toFixed(1)})`, 'success');
    } catch (e: any) { log(`Binarize failed: ${e.message}`, 'error'); }
  });

  btnUndoBinarize.addEventListener('click', async () => {
    try {
      await api.undoBinarizeImage(state.sessionId);
      await reloadImage();
      btnUndoBinarize.classList.add('hidden');
      btnBinarize.classList.remove('hidden');
      log('Binarization undone', 'success');
    } catch (e: any) { log(`Undo binarize failed: ${e.message}`, 'error'); }
  });

  btnTrim?.addEventListener('click', () => {
    if (state.currentMode === 'trim') {
      state.currentMode = 'view';
      btnTrim.classList.remove('active');
      clearOverlay();
    } else {
      state.currentMode = 'trim';
      btnTrim.classList.add('active');
      log('Draw a rectangle on the image to trim', 'info');
    }
    state.notify();
  });

  setTrimCompleteHandler(async (x, y, w, h) => {
    try {
      const result = await api.trimImage(state.sessionId, x, y, w, h);
      state.currentMode = 'view';
      btnTrim?.classList.remove('active');
      clearOverlay();
      await reloadImage();
      log(`Trimmed to ${result.width}x${result.height}`, 'success');
      state.notify();
    } catch (e: any) { log(`Trim failed: ${e.message}`, 'error'); }
  });

  // Subscription for enabling/disabling buttons
  state.subscribe(() => {
      const hasImage = state.hasImage;
      if (btnRotate) btnRotate.disabled = !hasImage;
      if (btnContrast) btnContrast.disabled = !hasImage;
      if (btnBinarize) btnBinarize.disabled = !hasImage;
      if (btnTrim) btnTrim.disabled = !hasImage;
      
      if (!hasImage) {
          if (imageInfo) imageInfo.textContent = '';
          btnUndoBinarize?.classList.add('hidden');
          btnBinarize?.classList.remove('hidden');
          const labelSpan = document.querySelector('#image-drop-zone .upload-label span');
          if (labelSpan) labelSpan.textContent = 'Upload Seismogram';
          updateWorkspaceFilename(null);
      }
  });
}

export async function reloadImage() {
  const url = api.getImageUrl(state.sessionId);
  try {
      const resp = await fetch(url);
      const scaleHeader = resp.headers.get('X-Display-Scale');
      state.displayScale = scaleHeader ? parseFloat(scaleHeader) : 1.0;
      await loadImage(url);
  } catch(e) {}
}

function showPPIRequiredModal(onConfirm: (ppi: number) => void) {
  const container = document.createElement('div');

  const warning = document.createElement('p');
  warning.className = 'modal-warning-text';
  warning.textContent =
    'We could not detect the pixel density (PPI) for this image automatically. ' +
    'Enter it below for accurate scaling. Without a valid PPI, scale definition ' +
    'and vectorization will stay disabled.';
  container.appendChild(warning);

  const group = document.createElement('div');
  group.className = 'form-group';
  const label = document.createElement('label');
  label.textContent = 'Pixels Per Inch (PPI):';
  const input = document.createElement('input');
  input.type = 'number';
  input.name = 'ppi';
  input.step = '1';
  input.min = '1';
  input.placeholder = 'e.g. 600';
  group.appendChild(label);
  group.appendChild(input);
  container.appendChild(group);

  const modal = new Modal({
    title: 'PPI Required',
    content: container,
    confirmText: 'Set PPI',
    cancelText: 'Continue Without PPI',
    onConfirm: (data) => {
      const ppi = parseFloat(data.ppi);
      if (!ppi || ppi <= 0) {
        log('Invalid PPI value — scale definition and vectorization stay disabled', 'error');
        return;
      }
      onConfirm(ppi);
    },
    onCancel: () => {
      log('Continuing without PPI — scale definition and vectorization are disabled until PPI is set', 'info');
    },
  });
  modal.show();
}

function setUploadLabelLoaded() {
  const labelSpan = document.querySelector('#image-drop-zone .upload-label span');
  if (labelSpan) labelSpan.textContent = 'Load New Image';
}

export function updateWorkspaceFilename(filename: string | null | undefined) {
  const el = document.getElementById('workspace-filename');
  if (!el) return;
  el.textContent = filename ? filename.replace(/\.[^/.]+$/, '') : '';
}

export function setPpiInputValue(ppi: number | null) {
  const ppiInput = document.getElementById('ppi-input') as HTMLInputElement | null;
  if (ppiInput) ppiInput.value = ppi ? String(ppi) : '';
}
