# Smart Cane Companion

An AI-powered, fully offline wearable navigation aid for visually impaired users. It fuses real-time object detection with head-level ultrasonic proximity sensing, and delivers feedback through spatial audio beeps and voice alerts — hands-free, low-latency, and running entirely on edge hardware with no cloud dependency.

<p align="center">
  <img src="docs/demo.gif" alt="Interactive hardware guide preview — hover states cycling through each module" width="420">
</p>

<p align="center">
  <b><a href="docs/hardware-guide.html">▶ Open the interactive hardware guide</a></b> — hover any module for its description (GitHub can't run the real hover interaction inside this README, so the GIF above is a recorded preview; the linked file is fully interactive)
</p>

## Hardware

| Module | Hardware | Placement | Purpose |
|---|---|---|---|
| **Headband** | 3× ultrasonic sensors (1 front, 2 side) + ESP32 | Worn on the head | Sweeps exactly where the user is looking, for immediate head-level obstacle awareness |
| **Camera** | USB webcam (or smartphone IP camera, `192.168.1.x:8080/video`) | Chest-mounted / hand-held | Stable, hands-free field of view for the vision pipeline |
| **Belt pouch** | Raspberry Pi 4 + power bank (min. 5V/3A) | Worn on the belt | Headless main hub — runs AI inference and audio mixing; powers the camera and ESP32 |
| **Audio out** | Earphones / Bluetooth headphones | In-ear | Voice alerts and spatial proximity beeps |
| **Tactile button** *(optional)* | Physical Pin 11 (GPIO 17) + Physical Pin 9 (GND), internal pull-up | On the housing | Manual trigger/interrupt, tested but optional |

The ESP32 talks to the Pi over **USB serial**.

## Software architecture

Multi-process by design, so the AI workload never blocks real-time sensor polling:

```
startup_manager.py  →  launches vision.py and ultrasonic.py as independent
                        parallel subprocesses; verifies camera/serial readiness first
       │
       ├── vision.py        Captures + resizes frames, frame-skips to hold FPS,
       │                    runs YOLO (NCNN) inference, fires voice alerts on a
       │                    separate thread (via paplay) so playback never
       │                    stalls the camera buffer. Uses /dev/shm (RAM-disk)
       │                    for fast inter-process handoff.
       │
       └── ultrasonic.py    Reads serial data from the ESP32, maps proximity
                             readings to Left/Center/Right channels, and plays
                             spatial beeps via pygame. Auto-reconnects on
                             dropped USB serial (try/except loop).
```

### The ML model

- **Architecture:** YOLOv8
- **Training:** dataset curated in Roboflow, trained on Kaggle Notebooks (cloud GPU)
- **Detects:** Stairs, Vehicles, Doors, Persons — with custom logic that groups overlapping "Person" detections into a single "Crowd ahead" warning
- **Deployment:** `best.pt` (PyTorch) exported to **NCNN** (`best_ncnn_model/`) — NCNN is optimized for ARM/edge devices, giving the Pi stable real-time FPS with no GPU

### Audio system

- `alert.mp3` — spoken/hazard alert, triggered by `vision.py` on a new detected hazard, with a >3.5s cooldown before repeating the same hazard (prevents nagging)
- `beep.mp3` — spatial proximity beep, triggered by `ultrasonic.py`, panned Left/Center/Right based on which sensor is closest to an obstacle

> Earlier planning discussed a richer set of per-hazard `.wav` files (`Stairs.wav`, `Vehicle.wav`, `Door.wav`, `P-left.wav`, `System Ready.wav`) played via `paplay` for lower decoding overhead. The current build on the Pi uses the two generic files above — update this section if that's changed since.

## Repo structure

```
.
├── docs/
│   ├── hardware-guide.html    # interactive hotspot diagram
│   └── demo.gif
├── src/
│   ├── startup_manager.py
│   ├── ultrasonic.py
│   └── vision.py
├── models/
│   ├── best.pt
│   └── best_ncnn_model/
├── sounds/
│   ├── alert.mp3
│   └── beep.mp3
├── requirements.txt
├── LICENSE
└── README.md
```

## Setup & run

1. Flash **Raspberry Pi OS 64-bit (Bookworm)**, headless mode with console autologin enabled (`raspi-config`) so audio drivers initialize without a desktop environment.
2. Install system packages:
   ```bash
   sudo apt install pulseaudio-utils
   ```
3. Create and activate the virtual environment:
   ```bash
   python3 -m venv yolo-env
   source yolo-env/bin/activate
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   python src/startup_manager.py
   ```
   This handles the full boot sequence — camera/serial checks, then launches `vision.py` and `ultrasonic.py`.

## Known issues / TODO

- **Power/USB instability:** running the Pi CPU at max load alongside a USB camera and the ESP32 can cause brief voltage drops → split-second USB disconnects. `ultrasonic.py`'s serial reconnect loop handles this, but a more robust power supply (or powered USB hub) would reduce how often it triggers.

## Viewing the interactive guide

- **Locally:** open `docs/hardware-guide.html` directly in any browser — self-contained, no server needed.
- **Online:** enable GitHub Pages (Settings → Pages → Deploy from branch → `main` / `docs`), then it's live at
  `https://<your-username>.github.io/<repo-name>/hardware-guide.html`

## License

Released under the [MIT License](LICENSE).
