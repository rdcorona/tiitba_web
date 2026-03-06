/**
 * Typed API client for the TIITBA backend.
 */

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, options);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

// --- Sessions ---

export async function createSession(): Promise<{ session_id: string }> {
  return request('/sessions', { method: 'POST' });
}

export async function getSessionInfo(sid: string) {
  return request<{
    session_id: string;
    has_image: boolean;
    has_points: boolean;
    has_data: boolean;
    has_scale: boolean;
    scale_mode: string | null;
    point_count: number;
  }>(`/sessions/${sid}`);
}

export async function deleteSession(sid: string) {
  return request(`/sessions/${sid}`, { method: 'DELETE' });
}

// --- Images ---

export async function uploadImage(sid: string, file: File, ppi?: number) {
  const form = new FormData();
  form.append('file', file);
  if (ppi) form.append('ppi', String(ppi));
  return request<{
    filename: string;
    ppi: number | null;
    width: number;
    height: number;
    width_mm: number | null;
    height_mm: number | null;
  }>(`/sessions/${sid}/image`, { method: 'POST', body: form });
}

export function getImageUrl(sid: string): string {
  return `${BASE}/sessions/${sid}/image?t=${Date.now()}`;
}

export async function rotateImage(sid: string) {
  return request<{ width: number; height: number }>(
    `/sessions/${sid}/image/rotate`, { method: 'POST' }
  );
}

export async function enhanceContrast(sid: string, clipLimit = 2.2, tileSize = 8) {
  return request<{ width: number; height: number }>(
    `/sessions/${sid}/image/contrast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clip_limit: clipLimit, tile_size: tileSize }),
    }
  );
}

export async function binarizeImage(sid: string) {
  return request<{ threshold: number }>(
    `/sessions/${sid}/image/binarize`, { method: 'POST' }
  );
}

export async function undoBinarizeImage(sid: string) {
  return request<{ width: number; height: number }>(
    `/sessions/${sid}/image/binarize/undo`, { method: 'POST' }
  );
}

export async function trimImage(sid: string, x: number, y: number, w: number, h: number) {
  return request<{ width: number; height: number }>(
    `/sessions/${sid}/image/trim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y, width: w, height: h }),
    }
  );
}

export async function getImageInfo(sid: string) {
  return request<{
    rows: number; cols: number;
    width_mm: number; height_mm: number; ppi: number;
  }>(`/sessions/${sid}/image/info`);
}

// --- Vectorization ---

export async function setTimemarks(sid: string, points: number[][], ppi: number) {
  return request<{ drum_speed: number; amp0: number; mean_distance_px: number }>(
    `/sessions/${sid}/scale/timemarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ points, ppi }),
    }
  );
}

export async function setCorners(sid: string, leftX: number, upY: number, rightX: number, downY: number) {
  return request(`/sessions/${sid}/scale/corners`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ left_x: leftX, up_y: upY, right_x: rightX, down_y: downY }),
  });
}

export async function addPoint(sid: string, x: number, y: number) {
  return request<{ index: number; time_or_x: number; amplitude_or_y: number }>(
    `/sessions/${sid}/points`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x, y }),
    }
  );
}

export async function removeLastPoint(sid: string) {
  return request<{ removed: number[]; remaining: number }>(
    `/sessions/${sid}/points/last`, { method: 'DELETE' }
  );
}

export async function clearPoints(sid: string) {
  return request(`/sessions/${sid}/points`, { method: 'DELETE' });
}

export async function getPlotData(sid: string) {
  return request<{
    time: number[]; amplitude: number[];
    xlabel: string; ylabel: string;
  }>(`/sessions/${sid}/plot-data`);
}

// --- Corrections ---

export async function uploadData(sid: string, file: File) {
  const form = new FormData();
  form.append('file', file);
  return request<{ n_samples: number; time_range: number[]; filename: string }>(
    `/sessions/${sid}/data/upload`, { method: 'POST', body: form }
  );
}

export async function getDataPlot(sid: string, series = 'raw') {
  return request<{ traces: { name: string; x: number[]; y: number[] }[] }>(
    `/sessions/${sid}/data/plot?series=${series}`
  );
}

export async function invertPolarity(sid: string) {
  return request(`/sessions/${sid}/corrections/polarity`, { method: 'POST' });
}

export async function detrend(sid: string, windowSize: number) {
  return request(`/sessions/${sid}/corrections/detrend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ window_size: windowSize }),
  });
}

export async function curvatureCorrection(
  sid: string, drumSpeed: number, styletLength: number,
  inflectionAmp: number, sps: number, splineOrder: string,
) {
  return request(`/sessions/${sid}/corrections/curvature`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      drum_speed: drumSpeed, stylet_length: styletLength,
      inflection_amp: inflectionAmp, sps, spline_order: splineOrder,
    }),
  });
}

export async function resampleData(sid: string, sps: number, splineOrder: string) {
  return request(`/sessions/${sid}/corrections/resample`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sps, spline_order: splineOrder }),
  });
}

export async function wiechertResponse(
  sid: string, T0: number, epsilon: number,
  V0: number, waterLevel: number, deconvolve: boolean,
) {
  return request(`/sessions/${sid}/corrections/wiechert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ T0, epsilon, V0, water_level: waterLevel, deconvolve }),
  });
}

// --- Export ---

export function getExportUrl(sid: string, format: string, dataType: string): string {
  return `${BASE}/sessions/${sid}/export/${format}?data=${dataType}`;
}
