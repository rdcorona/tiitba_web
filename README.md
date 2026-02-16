# TIITBA Web v1.0

**Historical Seismograms Vectorization, Analysis, and Correction - Web Application**

A web-based version of TIITBA built with FastAPI (Python) and vanilla TypeScript. Upload high-resolution seismogram images, digitize traces interactively on an HTML5 canvas, apply signal processing corrections, and export results in ASCII, SAC, or MINISEED formats.

## Architecture

- **Backend**: FastAPI + OpenCV (headless) + ObsPy + NumPy/SciPy
- **Frontend**: TypeScript + Vite + Plotly.js (no framework)
- **Session state**: In-memory per-user sessions with automatic TTL expiry

## Quick Start

### 1. Backend

```bash
cd tiitba_webapp
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# or: .venv\Scripts\activate  # Windows

pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser. The Vite dev server proxies API requests to the backend on port 8000.

### Production Build

```bash
cd frontend
npm run build
# Built files go to frontend/dist/, served by FastAPI automatically
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker build -t tiitba-web .
docker run -p 8000:8000 tiitba-web
```

## Workflow

1. **Upload Image** - Load a high-resolution seismogram scan
2. **Process** - Rotate, enhance contrast (CLAHE), binarize (Otsu), trim
3. **Define Scale** - Pick time-marks on the image or enter corner coordinates
4. **Vectorize** - Double-click to mark points along the trace (Z=undo, Esc=stop)
5. **Apply Corrections** - Detrend, curvature correction, resample, Wiechert response
6. **Export** - Download as ASCII, SAC, or MINISEED

## API Documentation

With the backend running, visit http://localhost:8000/docs for the interactive Swagger UI.

## Project Structure

```
tiitba_webapp/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Settings
│   ├── session.py            # Session state management
│   ├── dependencies.py       # FastAPI dependency injection
│   ├── schemas.py            # Pydantic models
│   ├── utils.py              # Image encoding utilities
│   ├── core/                 # Business logic (pure Python)
│   │   ├── corrections.py    # Detrend, G&A94, resample, Wiechert
│   │   ├── image_processing.py  # OpenCV operations
│   │   ├── io.py             # ASCII, SAC, MINISEED I/O
│   │   ├── vectorization.py  # Pixel-to-physical conversion
│   │   └── math_helpers.py   # Numerical utilities
│   └── routers/
│       ├── images.py         # Image upload and processing
│       ├── vectorization.py  # Scale definition and points
│       ├── corrections.py    # Signal processing corrections
│       └── export.py         # File format exports
├── frontend/
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── main.ts           # App initialization
│       ├── api.ts            # Backend API client
│       ├── state.ts          # Client state management
│       ├── components/       # UI components
│       └── utils/            # Canvas math, keyboard shortcuts
├── requirements.txt
├── Dockerfile
└── README.md
```

## Citation

If you use TIITBA to obtain time series or any result, please cite:

> Corona-Fernandez, R.D. & Santoyo, M.A. (2022) Re-examination of the 1928 Parral, Mexico earthquake (M6.3). *Geoscience Data Journal*. https://doi.org/10.1002/gdj3.159

## License

See [LICENSE](LICENSE) for terms.
