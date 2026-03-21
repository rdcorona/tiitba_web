/**
 * TIITBA Web Application - Main entry point.
 *
 * Initializes session, mounts all components, handles tab switching.
 */

import { createSession } from './api';
import { state } from './state';
import { initCanvas } from './components/canvas-viewer';
import { initImagePanel } from './components/image-panel';
import { initVectorizationPanel } from './components/vectorization-panel';
import { initCorrectionsPanel } from './components/corrections-panel';
import { log } from './components/info-log';

async function init() {
  // Create backend session
  try {
    const { session_id } = await createSession();
    state.sessionId = session_id;
    document.getElementById('session-indicator')!.textContent = `Session: ${session_id.slice(0, 8)}...`;
    log('Session created', 'success');
  } catch (e: any) {
    log(`Failed to create session: ${e.message}. Is the backend running?`, 'error');
    return;
  }

  // Initialize components
  initCanvas();
  initImagePanel();
  initVectorizationPanel();
  initCorrectionsPanel();

  // Tab switching (Left panel)
  const tabButtons = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.panel');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = (btn as HTMLElement).dataset.tab!;
      tabButtons.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`panel-${tab}`)!.classList.add('active');
    });
  });

  // Workspace tab switching (Center panel)
  const workspaceTabs = document.querySelectorAll('.workspace-tab');
  const workspaceViews = document.querySelectorAll('.workspace-view');
  
  workspaceTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = (btn as HTMLElement).dataset.target!;
      workspaceTabs.forEach(b => b.classList.remove('active'));
      workspaceViews.forEach(v => v.classList.add('hidden'));
      btn.classList.add('active');
      document.getElementById(target)!.classList.remove('hidden');
      window.dispatchEvent(new Event('resize')); // Resize Plotly or Canvas if needed
    });
  });
// Theme switching
const themeToggle = document.getElementById('theme-toggle')!;
const iconSun = document.getElementById('theme-icon-sun')!;
const iconMoon = document.getElementById('theme-icon-moon')!;
const unamLogo = document.querySelector('.unam-logo') as HTMLImageElement;
let isLightMode = false;

themeToggle.addEventListener('click', () => {
  isLightMode = !isLightMode;
  if (isLightMode) {
    document.documentElement.setAttribute('data-theme', 'light');
    iconSun.classList.add('hidden');
    iconMoon.classList.remove('hidden');
    if (unamLogo) unamLogo.src = '/logo_unam.png';
  } else {
    document.documentElement.removeAttribute('data-theme');
    iconMoon.classList.add('hidden');
    iconSun.classList.remove('hidden');
    if (unamLogo) unamLogo.src = '/logo-unam_lpng.png';
  }
});
    // Dispatch event to update plots
    window.dispatchEvent(new Event('themeChanged'));

  log('Tiitba-Web v1.0 ready', 'info');
}

init();
