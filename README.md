# Smart Cane Companion

A wearable, AI-assisted navigation aid for visually impaired users. Ultrasonic head-level obstacle detection, a hand-held vision camera, and real-time audio feedback — all run off a belt-mounted Raspberry Pi.

<p align="center">
  <img src="docs/demo.gif" alt="Interactive hardware guide preview — hover states cycling through each module" width="420">
</p>

<p align="center">
  <b><a href="https://jobil-libu.github.io/Wearable-Navigation-System-for-Visually-Impaired-People/">▶ Open the live interactive guide</a></b>
</p>

## How it works

| Module | Hardware | Placement | Purpose |
|---|---|---|---|
| **Headband** | 3× ultrasonic sensors (1 front, 2 side) + ESP32 | Worn on the head | Sweeps exactly where the user is looking, for immediate head-level obstacle awareness |
| **Hand-held camera** | USB webcam | Held freely in hand | Lets the user actively point and scan in any direction for the vision pipeline |
| **Belt pouch** | Raspberry Pi 4 + power bank | Worn on the belt | Houses the processing unit and battery out of the way; wires run down from the headband and camera |
| **Earpiece** | Earphone / bone-conduction earpiece | In-ear | Delivers real-time voice alerts (Pi) and spatial beeps (ESP32) without blocking ambient street noise |

## Repo structure

```
.
├── docs/
│   └── hardware-guide.html 
├── LICENSE
└── README.md
```

## Viewing the guide

- **Locally:** clone the repo and open `docs/hardware-guide.html` in any browser — it's a single self-contained file, no build step or server needed.
- **Online:** enable GitHub Pages for this repo (Settings → Pages → Deploy from branch → `main` / `docs`) and it'll be live at
  `https://<your-username>.github.io/<repo-name>/hardware-guide.html`

## Tech stack

- Vanilla HTML/CSS/JS for the interactive hardware guide
- ESP32 for on-headband ultrasonic sensing
- Raspberry Pi 4 for vision processing and voice alerts

## License

Released under the [MIT License](LICENSE).
