# GridFlow

GridFlow is a desktop simulator for an EV (electric vehicle) charging
station. A small C engine owns all of the simulation logic and state; a
PyQt6 desktop app reads that state through `ctypes` and renders it as a
live dashboard, including an isometric 2.5D view of the station yard.

## Features

- **Configurable number of sockets** (`NUM_SOCKETS` in `interface.py`), half
  AC (Type 2), half DC (CCS), each with its own realistic power ceiling
  (22 kW for AC, 120 kW for DC).
- **Dynamic grid load balancing** — if the combined demand of all actively
  charging vehicles exceeds the station's grid capacity, every session is
  throttled proportionally (fair share) instead of new vehicles being
  turned away.
- **Priority waiting queue** for when every matching socket is busy, with a
  rough estimated-wait-time calculation per vehicle.
- **Idle grace period + penalty fees** — a vehicle that reaches its target
  charge stops drawing power immediately, but starts accruing an idle fee
  if it keeps occupying the socket past a configurable grace period.
- **Persistent session statistics** — lifetime charging revenue, penalty
  revenue, and sessions served survive individual plug/unplug cycles.
- **Manual and random vehicle entry**, with adjustable priority.
- **Live charts** (grid load and lifetime revenue over simulated time),
  drawn with plain `QPainter` — no charting library dependency.
- **Isometric 2.5D station view** — a custom-drawn yard with per-socket
  charging bays, a holographic charge-level indicator, a day/night cycle
  with headlight glow, and an optional car sprite (falls back to a drawn
  car silhouette if the image asset is missing).

## Tech stack

| Layer              | Technology                                   |
|---------------------|-----------------------------------------------|
| Simulation engine   | C (C11)                                       |
| Desktop GUI         | Python 3 + PyQt6                              |
| C \u2194 Python bridge   | `ctypes` (stdlib, no extra binding library)   |
| Charts / 2.5D scene | Hand-rolled `QPainter` drawing (no charting or 3D engine dependency) |

## Architecture

The C side (`gridflow_core.h` + `station_manager.c`) is the single source
of truth: it owns the `Station`, `ChargingSocket`, `EVehicle` and
`WaitQueue` structs and every piece of simulation logic (charging math,
grid-load fair-share distribution, idle fees, queue estimates, lifetime
stats). It's compiled into a shared library and exposes a flat C API of
plain functions (`plugVehicle`, `advanceTime`, `getSocketSOC`, ...) — no
structs are passed across the language boundary, only primitives and
opaque `void*` handles.

The Python side (`interface.py`) never keeps its own copy of the
simulation state. Every view (the card dashboard, the statistics page, the
isometric view) re-reads everything it needs straight from the C library
through `ctypes` each time it refreshes, so the GUI can never drift out of
sync with the simulation.

## Project structure

```
.
├── gridflow_core.h     # Public C API, struct definitions
├── station_manager.c   # Simulation engine implementation
├── interface.py         # PyQt6 desktop GUI
└── assets/
    └── car_icon.png     # Optional car sprite for the isometric view
```

## Requirements

- A C compiler (GCC/MinGW recommended)
- Python 3.9+
- [PyQt6](https://pypi.org/project/PyQt6/)

```bash
pip install PyQt6
```

## Configuration & setup

### 1. Build the C engine into a shared library

`interface.py` loads the engine from `./gridflow.dll` via `ctypes`, so on
Windows, build it with that exact name:

```bash
gcc -shared -o gridflow.dll station_manager.c
```

> **Linux/macOS:** `ctypes.CDLL` can load a `.so`/`.dylib` just as well,
> but the loader path in `interface.py` (`dll_path = os.path.abspath('./gridflow.dll')`)
> is currently hardcoded to the `.dll` name. Either name your build output
> `gridflow.dll` regardless of platform, or point `dll_path` at your actual
> build artifact.

### 2. Place the car sprite (optional)

Put `car_icon.png` in an `assets/` folder next to `interface.py`. If it's
missing, the isometric view silently falls back to a drawn car silhouette
— nothing crashes either way.

### 3. Run the app

```bash
python interface.py
```

## Key configuration points

| Setting                         | Where                                   | Default |
|----------------------------------|------------------------------------------|---------|
| Number of sockets                | `NUM_SOCKETS` in `interface.py`          | 4       |
| Max grid capacity (kW)           | `initStation()` call in `interface.py`   | 500.0   |
| AC / DC price per kWh            | `initStation()` in `station_manager.c`   | 9.5 / 12.5 |
| Idle grace period (minutes)      | `initStation()` in `station_manager.c`   | 15      |
| Idle penalty fee (per minute)    | `initStation()` in `station_manager.c`   | 5.0     |
| AC / DC socket power ceiling     | `socketPowerLimit()` in `station_manager.c` | 22 kW / 120 kW |

## Notes

- Simulation state is in-memory only and resets every time the app is
  restarted — there is no save/load file yet.
- The station clock is simulated independently of real time; you advance
  it manually from the dashboard.