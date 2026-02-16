/**
 * Scrollable text log panel (replaces QTextEdit from desktop GUI).
 */

const logEl = () => document.getElementById('info-log')!;

export function log(message: string, type: 'info' | 'success' | 'error' | '' = '') {
  const entry = document.createElement('div');
  entry.className = `log-entry ${type}`;
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
  logEl().appendChild(entry);
  logEl().scrollTop = logEl().scrollHeight;
}

export function clearLog() {
  logEl().innerHTML = '';
}
