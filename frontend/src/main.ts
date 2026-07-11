/**
 * TIITBA Web Application - Main entry point.
 *
 * Initializes session, mounts all components, handles tab switching.
 */

import * as api from './api';
import { state } from './state';
import { initCanvas, refreshOverlay } from './components/canvas-viewer';
import { initImagePanel, reloadImage, updateWorkspaceFilename, setPpiInputValue } from './components/image-panel';
import { initVectorizationPanel } from './components/vectorization-panel';
import { initCorrectionsPanel } from './components/corrections-panel';
import { log } from './components/info-log';
import { Modal } from './components/modal';

async function showHistoryModal() {
  try {
    const history = await api.getSessionHistory();
    const container = document.createElement('div');
    container.className = 'history-list';

    if (history.length === 0) {
      container.innerHTML = '<p>No recent sessions found.</p>';
    } else {
      history.forEach(entry => {
        const item = document.createElement('div');
        item.className = 'history-item';
        const date = new Date(entry.timestamp * 1000).toLocaleString();
        item.innerHTML = `
          <div class="history-item-info">
            <strong>${entry.imagefile_name || entry.datafile_name || 'Unnamed Session'}</strong>
            <small>${date}</small>
            <span>${entry.point_count} points | ${entry.has_image ? 'Image' : 'Data'}</span>
          </div>
          <button class="btn btn-sm btn-primary btn-restore" data-sid="${entry.session_id}">Restore</button>
        `;
        container.appendChild(item);
      });
    }

    const modal = new Modal({
      title: 'Recent Sessions',
      content: container,
      cancelText: null,
      confirmText: 'Close'
    });

    modal.show();

    container.querySelectorAll('.btn-restore').forEach(btn => {
      (btn as HTMLElement).onclick = async () => {
        const sourceSid = (btn as HTMLElement).dataset.sid!;
        try {
          log(`Restoring session ${sourceSid.slice(0, 8)}...`, 'info');
          await api.restoreSession(state.sessionId, sourceSid);
          
          // Refresh full state
          const info = await api.getSessionInfo(state.sessionId);
          state.hasImage = info.has_image;
          state.hasData = info.has_data;
          state.hasScale = info.has_scale;

          if (state.hasImage) {
              const imgInfo = await api.getImageInfo(state.sessionId);
              state.ppi = imgInfo.ppi;
              setPpiInputValue(imgInfo.ppi);
              await reloadImage();
          }
          updateWorkspaceFilename(info.imagefile_name || info.datafile_name);

          // Restore digitized points onto the canvas overlay
          try {
            const pointsResult = await api.getPoints(state.sessionId);
            state.localPoints = pointsResult.points.map(([x, y]) => ({ x, y }));
            refreshOverlay();
          } catch {
            state.localPoints = [];
          }

          state.notify();
          log(`Session restored successfully (${state.localPoints.length} points)`, 'success');
          modal.hide();
        } catch (e: any) {
          log(`Restore failed: ${e.message}`, 'error');
        }
      };
    });
  } catch (e: any) {
    log(`Failed to load history: ${e.message}`, 'error');
  }
}

async function init() {
  // Create backend session
  try {
    const { session_id } = await api.createSession();
    state.sessionId = session_id;
    document.getElementById('session-indicator')!.textContent = `Session: ${session_id.slice(0, 8)}...`;
    log('Session created', 'success');
  } catch (e: any) {
    log(`Failed to create session: ${e.message}. Is the backend running?`, 'error');
    return;
  }

  // --- Main Navigation (Module Switching) ---
  const navItems = document.querySelectorAll('.nav-item[data-tab]');
  const panels = document.querySelectorAll('.panel');

  navItems.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = (btn as HTMLElement).dataset.tab!;
      
      navItems.forEach(b => b.classList.toggle('active', b === btn));
      panels.forEach(p => p.classList.toggle('active', p.id === `panel-${tabId}`));
      
      log(`Switched to ${tabId.toUpperCase()} module`, 'info');

      // Auto-load trigger for Corrections
      if (tabId === 'corrections' && !state.hasData) {
          api.autoLoadData(state.sessionId).then(result => {
              if (result) {
                  state.hasData = true;
                  log(`Auto-loaded data: ${result.filename}`, 'success');
                  state.notify();
              }
          }).catch(() => {});
      }
    });
  });

  // History button in side-nav
  document.getElementById('btn-session-history')?.addEventListener('click', showHistoryModal);

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
      window.dispatchEvent(new Event('resize'));
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
    window.dispatchEvent(new Event('themeChanged'));
  });

  // Auto-persist session
  setInterval(async () => {
    if (state.sessionId && (state.hasImage || state.hasData)) {
      try { await api.persistSession(state.sessionId); } catch(e) {}
    }
  }, 60000);

  // Initialize module-specific components
  initCanvas();
  initImagePanel();
  initVectorizationPanel();
  initCorrectionsPanel();

  log('Tiitba-Web ready', 'info');
}

init();
