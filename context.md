# TIITBA-Web - Context Documentation

## Overview
**TIITBA-Web (v1.0)** is a web-based application designed for the vectorization, analysis, and correction of historical seismograms. Users can upload high-resolution seismogram images, interactively digitize traces on a floating HTML5 canvas, apply signal processing corrections, and export results in various formats (ASCII, SAC, MINISEED).

## Architecture & Technology Stack

### Backend
- **Framework:** FastAPI (Python)
- **Core Libraries:** OpenCV (headless) for image processing, ObsPy for seismology tools, NumPy/SciPy for numerical utilities.
- **State Management:** In-memory, per-user sessions. The backend now supports "Undo Binarize" by storing the pre-binarization state.
- **Entry Point:** `backend/main.py`

### Frontend
- **Framework:** Vanilla TypeScript with Vite.
- **UI/UX Features:** 
  - **Floating Canvas Modal:** A non-blocking, draggable/resizable modal for image interaction, allowing simultaneous access to control panels.
  - **Theme Support:** Dark and Light themes with dynamic styling for both the UI and Plotly.js charts.
  - **Auto-Upload:** Images are uploaded and processed immediately upon selection.
- **Visualization:** Plotly.js for data plotting (with auto-scaling) and native HTML5 Canvas for interactive vectorization.
- **Entry Point:** `frontend/src/main.ts`

## Workflow

1. **Upload Image**: Select a seismogram scan (auto-upload).
2. **Process**: 
   - Operations: Rotation, contrast enhancement (CLAHE), binarization (Otsu).
   - **Undo Binarize:** Revert to the original image if binarization is not satisfactory.
   - **Trim:** Define a Region of Interest (ROI) directly on the canvas.
3. **Define Scale**: Pick 3+ time-marks (single-click) or enter corner coordinates.
4. **Vectorize**: Interactively mark points along the trace via single-clicks on the floating canvas.
5. **Apply Corrections**: Signal processing (detrending, curvature correction, resampling, Wiechert response).
6. **Export**: Download processed data in multiple formats.

## Project Structure

```text
tiitba_webapp/
├── backend/
│   ├── core/                 # Business logic (math, image proc, io)
│   ├── routers/              # API endpoints
│   ├── main.py               # FastAPI entry point
│   ├── session.py            # Session state (supports binarize undo)
│   └── ...
├── frontend/
│   ├── public/               # Static assets (logos, favicon)
│   ├── src/
│   │   ├── components/       # UI Components (canvas, panels, plots)
│   │   ├── styles/           # Theme-aware CSS
│   │   ├── api.ts            # API interaction layer
│   │   └── main.ts           # Theme toggle and app initialization
│   ├── index.html            # Main UI layout
│   └── ...
├── Dockerfile
├── requirements.txt          # Updated for Python 3.14 compatibility
└── context.md                # This file
```

## Running Locally

**Backend:**
```bash
python -m venv .venv
# Activate venv and install:
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Vite runs on port 5173 and proxies `/api` to port 8000.
