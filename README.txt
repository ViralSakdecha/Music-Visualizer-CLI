Music Visualizer CLI (Windows)
==============================

Real-time ASCII music visualizer for Windows terminal, with:
- Live system-audio FFT bars (WASAPI loopback)
- Real-time BPM estimation
- Now-playing metadata from active media session (Spotify, browser, VLC, etc.)
- Smooth curses-based animations and keyboard controls


Requirements
------------
- Windows 10/11
- Python 3.10+
- A Unicode-capable terminal (Windows Terminal recommended)


Install
-------
1. Clone the repo:
	git clone <your-repo-url>
	cd "Music Visualizer CLI"

2. (Optional but recommended) Create a virtual environment:
	python -m venv .venv
	.venv\Scripts\activate

3. Install dependencies:
	pip install -r requirements.txt

4. If needed for system volume polling in `audio_capture.py`, install:
	pip install pycaw comtypes


Run
---
python main.py

Make sure audio is actively playing through your default output device.


Controls
--------
- Q: Quit
- + / -: Increase or decrease sensitivity
- R: Reset visual smoothing/peaks


How It Works
------------
- `audio_capture.py`: Captures system output audio via WASAPI loopback and computes FFT bands.
- `bpm_detector.py`: Estimates BPM from spectral flux and autocorrelation.
- `media_info.py`: Reads current media metadata via Windows Media Control API (WinRT).
- `visualizer.py`: Renders animated ASCII bars and status UI with `curses`.
- `main.py`: Application loop, controls, and component orchestration.


Troubleshooting
---------------
- "WASAPI not available" or "Could not find a WASAPI loopback device":
  - Verify you are on Windows and an output device is active.
  - Start some audio playback and retry.

- No media title shown:
  - Ensure a supported app is playing media.
  - Confirm `winrt-Windows.Media.Control` is installed.

- Garbled symbols/colors:
  - Use Windows Terminal or another terminal with Unicode support.
  - Ensure your font supports box-drawing characters.

License
-------
This project is licensed under the MIT License.
See `LICENSE` for full details.
