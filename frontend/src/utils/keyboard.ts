/**
 * Global keyboard shortcut handler.
 */

type Handler = (e: KeyboardEvent) => void;

const handlers: Map<string, Handler> = new Map();

export function registerKey(key: string, handler: Handler) {
  handlers.set(key.toLowerCase(), handler);
}

export function unregisterKey(key: string) {
  handlers.delete(key.toLowerCase());
}

document.addEventListener('keydown', (e) => {
  // Don't capture when typing in inputs
  const tag = (e.target as HTMLElement).tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  const handler = handlers.get(e.key.toLowerCase());
  if (handler) {
    e.preventDefault();
    handler(e);
  }
});
