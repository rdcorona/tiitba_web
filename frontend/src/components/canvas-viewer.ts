/**
 * Interactive canvas for seismogram image display and point digitization.
 *
 * Two stacked canvases:
 * - image-canvas: displays the seismogram image
 * - overlay-canvas: draws points, lines, trim rectangles on top
 *
 * Supports pan (right-click drag), zoom (scroll wheel), and multiple
 * interaction modes (view, timemarks, vectorize, trim).
 */

import { state } from '../state';
import { Transform, displayToImage, imageToDisplay } from '../utils/canvas-math';

let imageCanvas: HTMLCanvasElement;
let overlayCanvas: HTMLCanvasElement;
let imageCtx: CanvasRenderingContext2D;
let overlayCtx: CanvasRenderingContext2D;
let container: HTMLElement;

let currentImage: HTMLImageElement | null = null;
let transform: Transform = { offsetX: 0, offsetY: 0, scale: 1 };
let isPanning = false;
let panStart = { x: 0, y: 0 };

// Trim rectangle state
let trimStart: { x: number; y: number } | null = null;
let trimRect: { x: number; y: number; w: number; h: number } | null = null;

// Callbacks
let onPointClick: ((imgX: number, imgY: number) => void) | null = null;
let onTrimComplete: ((x: number, y: number, w: number, h: number) => void) | null = null;

export function initCanvas() {
  container = document.getElementById('canvas-container')!;
  imageCanvas = document.getElementById('image-canvas') as HTMLCanvasElement;
  overlayCanvas = document.getElementById('overlay-canvas') as HTMLCanvasElement;
  imageCtx = imageCanvas.getContext('2d')!;
  overlayCtx = overlayCanvas.getContext('2d')!;

  resizeCanvases();
  window.addEventListener('resize', resizeCanvases);

  // Mouse events on overlay (top canvas)
  overlayCanvas.addEventListener('dblclick', handleDoubleClick);
  overlayCanvas.addEventListener('mousedown', handleMouseDown);
  overlayCanvas.addEventListener('mousemove', handleMouseMove);
  overlayCanvas.addEventListener('mouseup', handleMouseUp);
  overlayCanvas.addEventListener('wheel', handleWheel, { passive: false });
  overlayCanvas.addEventListener('contextmenu', (e) => e.preventDefault());
}

function resizeCanvases() {
  const rect = container.getBoundingClientRect();
  imageCanvas.width = rect.width;
  imageCanvas.height = rect.height;
  overlayCanvas.width = rect.width;
  overlayCanvas.height = rect.height;
  redraw();
}

export function loadImage(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      currentImage = img;
      fitToView();
      redraw();
      resolve();
    };
    img.onerror = reject;
    img.src = url;
  });
}

function fitToView() {
  if (!currentImage) return;
  const cw = imageCanvas.width;
  const ch = imageCanvas.height;
  const iw = currentImage.width;
  const ih = currentImage.height;
  const scale = Math.min(cw / iw, ch / ih) * 0.95;
  transform = {
    scale,
    offsetX: (cw - iw * scale) / 2,
    offsetY: (ch - ih * scale) / 2,
  };
}

function redraw() {
  drawImage();
  drawOverlay();
}

function drawImage() {
  imageCtx.clearRect(0, 0, imageCanvas.width, imageCanvas.height);
  if (!currentImage) return;
  imageCtx.save();
  imageCtx.translate(transform.offsetX, transform.offsetY);
  imageCtx.scale(transform.scale, transform.scale);
  imageCtx.drawImage(currentImage, 0, 0);
  imageCtx.restore();
}

function drawOverlay() {
  overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

  const points = state.localPoints;
  if (points.length === 0) return;

  const ds = state.displayScale;
  const mode = state.currentMode;
  const color = mode === 'timemarks' ? '#4caf50' : '#e94560';

  // Draw connecting lines
  if (points.length > 1 && mode === 'vectorize') {
    overlayCtx.beginPath();
    overlayCtx.strokeStyle = color;
    overlayCtx.lineWidth = 1;
    const first = imageToDisplay(points[0].x, points[0].y, transform, ds);
    overlayCtx.moveTo(first.x, first.y);
    for (let i = 1; i < points.length; i++) {
      const p = imageToDisplay(points[i].x, points[i].y, transform, ds);
      overlayCtx.lineTo(p.x, p.y);
    }
    overlayCtx.stroke();
  }

  // Draw points
  for (const pt of points) {
    const dp = imageToDisplay(pt.x, pt.y, transform, ds);
    overlayCtx.beginPath();
    overlayCtx.arc(dp.x, dp.y, 4, 0, Math.PI * 2);
    overlayCtx.fillStyle = color;
    overlayCtx.fill();
    overlayCtx.strokeStyle = '#fff';
    overlayCtx.lineWidth = 1;
    overlayCtx.stroke();
  }

  // Draw trim rectangle
  if (trimRect) {
    const tl = imageToDisplay(trimRect.x, trimRect.y, transform, ds);
    const br = imageToDisplay(
      trimRect.x + trimRect.w, trimRect.y + trimRect.h, transform, ds,
    );
    overlayCtx.strokeStyle = '#ff0';
    overlayCtx.lineWidth = 2;
    overlayCtx.setLineDash([5, 5]);
    overlayCtx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y);
    overlayCtx.setLineDash([]);
  }
}

// --- Event Handlers ---

function handleDoubleClick(e: MouseEvent) {
  if (state.currentMode === 'view') return;
  if (!currentImage) return;

  const rect = overlayCanvas.getBoundingClientRect();
  const dx = e.clientX - rect.left;
  const dy = e.clientY - rect.top;
  const imgCoords = displayToImage(dx, dy, transform, state.displayScale);

  if (onPointClick) {
    onPointClick(imgCoords.x, imgCoords.y);
  }
}

function handleMouseDown(e: MouseEvent) {
  // Right-click or middle-click = pan
  if (e.button === 2 || e.button === 1) {
    isPanning = true;
    panStart = { x: e.clientX - transform.offsetX, y: e.clientY - transform.offsetY };
    return;
  }

  // Left-click in trim mode = start rectangle
  if (state.currentMode === 'trim' && e.button === 0) {
    const rect = overlayCanvas.getBoundingClientRect();
    const dx = e.clientX - rect.left;
    const dy = e.clientY - rect.top;
    trimStart = displayToImage(dx, dy, transform, state.displayScale);
    trimRect = null;
  }
}

function handleMouseMove(e: MouseEvent) {
  if (isPanning) {
    transform.offsetX = e.clientX - panStart.x;
    transform.offsetY = e.clientY - panStart.y;
    redraw();
    return;
  }

  // Trim drag
  if (state.currentMode === 'trim' && trimStart && e.buttons === 1) {
    const rect = overlayCanvas.getBoundingClientRect();
    const dx = e.clientX - rect.left;
    const dy = e.clientY - rect.top;
    const current = displayToImage(dx, dy, transform, state.displayScale);
    trimRect = {
      x: Math.min(trimStart.x, current.x),
      y: Math.min(trimStart.y, current.y),
      w: Math.abs(current.x - trimStart.x),
      h: Math.abs(current.y - trimStart.y),
    };
    drawOverlay();
  }

  // Update status bar with coordinates
  if (currentImage) {
    const rect = overlayCanvas.getBoundingClientRect();
    const dx = e.clientX - rect.left;
    const dy = e.clientY - rect.top;
    const img = displayToImage(dx, dy, transform, state.displayScale);
    const status = document.getElementById('canvas-status')!;
    status.textContent = `Pixel: (${img.x}, ${img.y}) | Mode: ${state.currentMode}`;
  }
}

function handleMouseUp(e: MouseEvent) {
  if (isPanning) {
    isPanning = false;
    return;
  }

  // Trim release
  if (state.currentMode === 'trim' && trimStart && trimRect) {
    trimStart = null;
    if (trimRect.w > 5 && trimRect.h > 5 && onTrimComplete) {
      onTrimComplete(trimRect.x, trimRect.y, trimRect.w, trimRect.h);
    }
  }
}

function handleWheel(e: WheelEvent) {
  e.preventDefault();
  const rect = overlayCanvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
  const newScale = transform.scale * zoomFactor;

  // Zoom toward cursor
  transform.offsetX = mouseX - (mouseX - transform.offsetX) * zoomFactor;
  transform.offsetY = mouseY - (mouseY - transform.offsetY) * zoomFactor;
  transform.scale = newScale;

  redraw();
}

// --- Public API ---

export function setPointClickHandler(handler: (imgX: number, imgY: number) => void) {
  onPointClick = handler;
}

export function setTrimCompleteHandler(handler: (x: number, y: number, w: number, h: number) => void) {
  onTrimComplete = handler;
}

export function clearOverlay() {
  state.localPoints = [];
  trimRect = null;
  drawOverlay();
}

export function refreshOverlay() {
  drawOverlay();
}

export function removeLastOverlayPoint() {
  state.localPoints.pop();
  drawOverlay();
}
