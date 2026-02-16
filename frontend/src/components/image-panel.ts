/**
 * Image processing panel: upload, rotate, contrast, binarize, trim.
 */

import * as api from '../api';
import { state } from '../state';
import { log } from './info-log';
import { loadImage, setTrimCompleteHandler, clearOverlay } from './canvas-viewer';

export function initImagePanel() {
  const fileInput = document.getElementById('image-upload') as HTMLInputElement;
  const ppiInput = document.getElementById('ppi-input') as HTMLInputElement;
  const btnUpload = document.getElementById('btn-upload') as HTMLButtonElement;
  const btnRotate = document.getElementById('btn-rotate') as HTMLButtonElement;
  const btnContrast = document.getElementById('btn-contrast') as HTMLButtonElement;
  const btnBinarize = document.getElementById('btn-binarize') as HTMLButtonElement;
  const btnTrim = document.getElementById('btn-trim-mode') as HTMLButtonElement;
  const imageInfo = document.getElementById('image-info')!;

  fileInput.addEventListener('change', () => {
    btnUpload.disabled = !fileInput.files?.length;
  });

  btnUpload.addEventListener('click', async () => {
    if (!fileInput.files?.length) return;
    const file = fileInput.files[0];
    const ppi = ppiInput.value ? parseFloat(ppiInput.value) : undefined;

    try {
      btnUpload.disabled = true;
      btnUpload.textContent = 'Uploading...';
      const result = await api.uploadImage(state.sessionId, file, ppi);

      state.hasImage = true;
      state.ppi = result.ppi;
      state.imageWidth = result.width;
      state.imageHeight = result.height;
      state.notify();

      await reloadImage();

      log(`Loaded: ${result.filename} (${result.width}x${result.height})`, 'success');
      if (result.ppi) log(`PPI: ${result.ppi}`, 'info');
      if (result.width_mm) {
        imageInfo.textContent = `${result.width}x${result.height} px | ${result.width_mm.toFixed(1)}x${result.height_mm?.toFixed(1)} mm | PPI: ${result.ppi}`;
      } else {
        imageInfo.textContent = `${result.width}x${result.height} px | PPI: ${result.ppi ?? 'unknown'}`;
      }

      enableProcessButtons(true);
    } catch (e: any) {
      log(`Upload failed: ${e.message}`, 'error');
    } finally {
      btnUpload.disabled = false;
      btnUpload.textContent = 'Upload';
    }
  });

  btnRotate.addEventListener('click', async () => {
    try {
      const result = await api.rotateImage(state.sessionId);
      await reloadImage();
      log(`Rotated 90deg CW (${result.width}x${result.height})`, 'success');
    } catch (e: any) { log(`Rotate failed: ${e.message}`, 'error'); }
  });

  btnContrast.addEventListener('click', async () => {
    try {
      await api.enhanceContrast(state.sessionId);
      await reloadImage();
      log('CLAHE contrast enhancement applied', 'success');
    } catch (e: any) { log(`Contrast failed: ${e.message}`, 'error'); }
  });

  btnBinarize.addEventListener('click', async () => {
    try {
      const result = await api.binarizeImage(state.sessionId);
      await reloadImage();
      log(`Binarized (Otsu threshold: ${result.threshold.toFixed(1)})`, 'success');
    } catch (e: any) { log(`Binarize failed: ${e.message}`, 'error'); }
  });

  btnTrim.addEventListener('click', () => {
    if (state.currentMode === 'trim') {
      state.currentMode = 'view';
      btnTrim.textContent = 'Trim';
      clearOverlay();
    } else {
      state.currentMode = 'trim';
      btnTrim.textContent = 'Cancel Trim';
      log('Draw a rectangle on the image to trim', 'info');
    }
    state.notify();
  });

  setTrimCompleteHandler(async (x, y, w, h) => {
    try {
      const result = await api.trimImage(state.sessionId, x, y, w, h);
      state.currentMode = 'view';
      btnTrim.textContent = 'Trim';
      clearOverlay();
      await reloadImage();
      log(`Trimmed to ${result.width}x${result.height}`, 'success');
      state.notify();
    } catch (e: any) { log(`Trim failed: ${e.message}`, 'error'); }
  });

  function enableProcessButtons(enabled: boolean) {
    btnRotate.disabled = !enabled;
    btnContrast.disabled = !enabled;
    btnBinarize.disabled = !enabled;
    btnTrim.disabled = !enabled;
  }
}

async function reloadImage() {
  const url = api.getImageUrl(state.sessionId);
  // Fetch to get the display scale header
  const resp = await fetch(url);
  const scaleHeader = resp.headers.get('X-Display-Scale');
  state.displayScale = scaleHeader ? parseFloat(scaleHeader) : 1.0;

  await loadImage(url);
}
