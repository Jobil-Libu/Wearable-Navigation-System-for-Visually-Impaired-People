# Smart Cane Companion

An AI-powered, fully offline wearable navigation aid for visually impaired users. It fuses real-time object detection with head-level ultrasonic proximity sensing, and delivers feedback through spatial audio beeps and voice alerts — hands-free, low-latency, and running entirely on edge hardware with no cloud dependency.

<p align="center">
  <img src="docs/demo.gif" alt="Interactive hardware guide preview — hover states cycling through each module" width="420">
</p>

<p align="center">
  <b><a href="https://jobil-libu.github.io/Wearable-Navigation-System-for-Visually-Impaired-People">▶ Open the interactive hardware guide</a></b>
</p>

## Hardware

| Module | Hardware | Placement | Purpose |
|---|---|---|---|
| **Headband** | 3× ultrasonic sensors (1 front, 2 side) + ESP32 | Worn on the head | Sweeps exactly where the user is looking, for immediate head-level obstacle awareness — firmware in [`esp32/ultrasonic_headband/`](esp32/ultrasonic_headband/) |
| **Camera** | USB webcam (or smartphone IP camera, `192.168.1.x:8080/video`) | Chest-mounted / hand-held | Stable, hands-free field of view for the vision pipeline |
| **Belt pouch** | Raspberry Pi 4 + power bank (min. 5V/3A) | Worn on the belt | Headless main hub — runs AI inference and audio mixing; powers the camera and ESP32 |
| **Audio out** | Earphones / Bluetooth headphones | In-ear | Voice alerts and spatial proximity beeps |

The ESP32 talks to the Pi over **USB serial**.

## Circuit diagram

<p align="center">
  <img src="docs/circuit-diagram.png" alt="Circuit diagram — ESP32, ultrasonic sensors, Raspberry Pi 4, camera, and audio wiring" width="900">
</p>


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
`startup_manager.py` does more than just launch things — it's a real boot sequence:

1. Waits 5s, then speaks **"System initializing"** via a local **Piper TTS** engine (`/home/pi4/piper/piper` + a `.onnx` voice model) — output is synthesized to `/dev/shm/startup_msg.wav` (RAM-disk, for instant playback) and played with `paplay`.
2. Polls for the ESP32 (`/dev/ttyUSB*` / `/dev/ttyACM*`), repeating **"Connect Sensors"** every 4s until found, then confirms **"Sensors Connected"**.
3. Looks for a camera: a physical USB camera at `/dev/video0` first, otherwise a phone IP camera reached via the network gateway (`192.168.x.x:8080/video`) — repeating **"Connect Camera"** until one is found, then announces which kind.
4. Speaks **"Starting Navigation"**, then launches `vision.py` and `ultrasonic.py` as subprocesses, passing the camera source and ESP32 serial port to them as arguments.

> ⚠️ `VENV_PYTHON`, `APP_FOLDER`, `PIPER_BINARY`, and `MODEL_PATH` are hardcoded as absolute paths at the top of `startup_manager.py` (currently `/home/pi4/...`). If you ever deploy under a different username or folder, those constants need editing too — they won't pick up `assistivetech.service`'s `WorkingDirectory` automatically.

### ESP32 firmware (`esp32/ultrasonic_headband/`)

Runs independently of the Pi — polls the 3 headband ultrasonic sensors in a loop and streams the readings over USB serial for `ultrasonic.py` to consume.

| Sensor | Trig pin | Echo pin |
|---|---|---|
| Left | GPIO 5 | GPIO 18 |
| Center | GPIO 21 | GPIO 22 |
| Right | GPIO 19 | GPIO 23 |

- Each sensor is read with a standard trigger/echo pulse (`pulseIn`, 30ms timeout); a timed-out read reports `400` (treated as "nothing in range").
- A 15ms settle delay between each of the 3 reads prevents cross-talk/echo interference between sensors.
- Every loop, it sends one CSV line over serial: `L,C,R` (distances in cm), at **115200 baud** — this is the exact format `ultrasonic.py` parses on the Pi side.


### The ML model

- **Architecture:** YOLOv8
- **Training:** dataset curated in Roboflow and some custom dataset, trained on Kaggle Notebooks (cloud GPU)
- **Detects:** Stairs, Vehicles, Doors, Persons — with custom logic that groups overlapping "Person" detections into a single "Crowd ahead" warning
- **Deployment:** `best.pt` (PyTorch) exported to **NCNN** (`best_ncnn_model/`) — NCNN is optimized for ARM/edge devices, giving the Pi stable real-time FPS with no GPU

### Audio system

Three separate audio mechanisms run side by side:

1. **Boot announcements — Piper TTS.** `startup_manager.py` synthesizes short status lines ("System initializing", "Connect Sensors", "Sensors Connected", "Connect Camera", "USB/Phone Camera Found", "Starting Navigation") on the fly with a local Piper voice model, rather than pre-recorded files.

2. **Per-hazard spoken alerts — `AssistiveTech/sounds/`.** `vision.py` maps each detection directly to a `.wav` file via an `AUDIO_MAP` dict, played with `paplay`:

   | Detection | Sound file |
   |---|---|
   | Stairs Ahead | `Stairs.wav` |
   | Vehicle Ahead | `Vehicle.wav` |
   | Door Ahead | `Door.wav` |
   | Crowd ahead (>3 people) | `Crowd ahead.wav` |
   | Person left | `P-left.wav` |
   | Person right | `P-right.wav` |
   | Person ahead | `P-ahead.wav` |
   | System Ready | `System Ready.wav` |

   Detections are ranked by priority (hazard > navigation > info) and only the top one is spoken per frame. A message repeats only if it's new (>2.5s since the last one) or the same one has been silent for >3.5s — so it won't nag, but also won't go silent for long.

3. **Continuous spatial proximity beeps — `alert.mp3` / `beep.mp3`.** `ultrasonic.py` loops these on separate pygame channels rather than firing one-shot beeps: `alert.mp3` on the **left/right** channels, `beep.mp3` on the **center** channel. Volume is a smoothed, distance-based curve (median-filtered over 5 samples, capped at 35%, decaying gradually rather than snapping) — and when something is dead ahead, the side channels are automatically ducked to 20% volume so a center-priority hazard doesn't get drowned out by side noise.


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
   python AssistiveTech/startup_manager.py
   ```
## Running automatically on boot (systemd service)

`startup_manager.py` is set up to launch on every boot via a systemd service, `assistivetech.service`.

**Install it (one-time setup):**
```bash
sudo cp assistivetech.service /etc/systemd/system/assistivetech.service
sudo systemctl daemon-reload
sudo systemctl enable assistivetech.service   # start on every future boot
sudo systemctl start assistivetech.service    # start it right now
```
> Before installing, open `assistivetech.service` and edit the `User`, `WorkingDirectory`, and `ExecStart` lines to match where the repo actually lives on your Pi (and the venv path if it's not `yolo-env`).

**Day-to-day commands:**
```bash
# Watch live logs to confirm it's running on boot
sudo journalctl -u assistivetech.service -f

# Stop it immediately
sudo systemctl stop assistivetech.service

# Check the Python process directly / kill it by hand if needed
ps aux | grep startup_manager.py
kill <pid>
```


## Known issues

- **Power/USB instability:** running the Pi CPU at max load alongside a USB camera and the ESP32 can cause brief voltage drops → split-second USB disconnects. `ultrasonic.py`'s serial reconnect loop handles this, but a more robust power supply (or powered USB hub) would reduce how often it triggers.

> [!WARNING]
> **Custom Path Configuration Required**
> This codebase currently uses absolute directory paths tailored to the original Raspberry Pi development environment
> 
> Before executing the system on your own hardware, you **must** open the configuration sections at the top of `vision.py` and `startup_manager.py` and update the paths to match your local file structure. Failure to do so will result in missing file errors for the AI models and audio clips.

## License

Released under the [MIT License](LICENSE).
