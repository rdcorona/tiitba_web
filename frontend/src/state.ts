/**
 * Client-side observable state with event emitter pattern.
 */

type Listener = () => void;

class AppState {
  sessionId = '';
  hasImage = false;
  hasScale = false;
  hasData = false;
  currentMode: 'view' | 'timemarks' | 'vectorize' | 'trim' = 'view';
  isVectorizing = false;
  localPoints: { x: number; y: number }[] = [];
  displayScale = 1.0;
  imageWidth = 0;
  imageHeight = 0;
  ppi: number | null = null;

  private listeners: Listener[] = [];

  subscribe(fn: Listener): () => void {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter(l => l !== fn);
    };
  }

  notify() {
    this.listeners.forEach(fn => fn());
  }
}

export const state = new AppState();
