"""
main.py — Entry point for the ASCII Music Visualizer CLI.
"""

import curses
import time
import sys
import numpy as np

from audio_capture import AudioCapture
from media_info import MediaInfo
from bpm_detector import BPMDetector
from visualizer import Visualizer


def print_splash():
    splash = """
\033[36m
     ┌──────────────────────────────────────────────┐
     │                                              │
     │    ♪  A U D I O   V I S U A L I Z E R  ♪    │
     │                                              │
     │         Capturing system audio...            │
     │         Make sure music is playing!           │
     │                                              │
     └──────────────────────────────────────────────┘
\033[0m"""
    print(splash)


def main(stdscr):
    try:
        audio = AudioCapture(chunk_size=2048)
    except RuntimeError as e:
        curses.endwin()
        print(f"\n  \033[31m✖ Audio Error: {e}\033[0m")
        print("  Make sure audio is playing through your speakers.\n")
        sys.exit(1)

    media = MediaInfo()
    bpm = BPMDetector(sample_rate=audio.sample_rate)
    viz = Visualizer(stdscr)

    audio.start()
    media.start()

    sensitivity = 1.0
    start_time = time.time()

    try:
        while True:
            key = stdscr.getch()
            if key == ord("q") or key == ord("Q"):
                break
            elif key == ord("+") or key == ord("="):
                sensitivity = min(sensitivity + 0.2, 5.0)
            elif key == ord("-") or key == ord("_"):
                sensitivity = max(sensitivity - 0.2, 0.2)
            elif key == ord("r") or key == ord("R"):
                viz.prev_bars = None
                viz.peaks = None

            # FFT
            max_y, max_x = stdscr.getmaxyx()
            num_bars = min(64, (max_x - 6) // 3)
            fft_bands = audio.get_fft(num_bars=num_bars)
            fft_bands = np.clip(fft_bands * sensitivity, 0, 1)

            # Volume
            _, volume = audio.get_audio_data()

            # BPM
            audio_data, _ = audio.get_audio_data()
            bpm.process(audio_data)
            current_bpm = bpm.get_bpm()

            # Media
            media_text = media.get_display_string()

            # Elapsed
            elapsed = time.time() - start_time

            # Render
            viz.render(fft_bands, volume, current_bpm, media_text, elapsed)

            time.sleep(0.033)

    except KeyboardInterrupt:
        pass
    finally:
        audio.stop()
        media.stop()


if __name__ == "__main__":
    print_splash()
    time.sleep(0.5)

    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"\n  \033[31m✖ Error: {e}\033[0m")
        print("  Make sure your terminal supports Unicode & colors.\n")
        sys.exit(1)

    print("\n  \033[36m♪ Thanks for vibing! ♪\033[0m\n")
