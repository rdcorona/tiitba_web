/**
 * Scrollable text log panel (replaces QTextEdit from desktop GUI).
 *
 * Split into two tabs so rapid vectorization clicks don't drown out
 * general app messages: "general" (uploads, processing, corrections,
 * exports, session events) and "vectorization" (scale/point picking).
 */

type LogCategory = 'general' | 'vectorization';

const logEl = (category: LogCategory) =>
  document.getElementById(
    category === 'vectorization' ? 'info-log-vectorization' : 'info-log-general'
  )!;

export function log(
  message: string,
  type: 'info' | 'success' | 'error' | '' = '',
  category: LogCategory = 'general',
) {
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  const el = logEl(category);
  el.appendChild(entry);
  el.scrollTop = el.scrollHeight;
}

export function clearLog(category?: LogCategory) {
  if (category) {
    logEl(category).innerHTML = '';
  } else {
    logEl('general').innerHTML = '';
    logEl('vectorization').innerHTML = '';
  }
}

export function initInfoLog() {
  const panel = document.querySelector('.info-log-panel') as HTMLElement | null;
  const appLayout = document.querySelector('.app-layout') as HTMLElement | null;
  const tabs = document.querySelectorAll<HTMLElement>('.info-log-panel .tab-btn');
  const contents = document.querySelectorAll<HTMLElement>('.info-log-panel .log-tab-content');
  const collapseBtn = document.getElementById('btn-collapse-log');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.logTab;
      tabs.forEach(t => t.classList.toggle('active', t === tab));
      contents.forEach(c => c.classList.toggle('hidden', c.dataset.logTab !== target));
    });
  });

  collapseBtn?.addEventListener('click', () => {
    const collapsed = panel?.classList.toggle('collapsed') ?? false;
    appLayout?.classList.toggle('log-collapsed', collapsed);
    const label = collapsed ? 'Expand log' : 'Collapse log';
    collapseBtn.title = label;
    collapseBtn.setAttribute('aria-label', label);
  });
}
