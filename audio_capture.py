"""
audio_capture.py — Captures system audio via WASAPI loopback.
Uses pycaw for real Windows system volume.
"""

import pyaudiowpatch as pyaudio
import numpy as np
import threading
import time


class AudioCapture:
    def __init__(self, chunk_size=2048):
        self.chunk_size = chunk_size
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.audio_data = np.zeros(chunk_size)
        self.lock = threading.Lock()

        # System volume via pycaw
        self._sys_volume = 0.0
        self._vol_thread = None

        self._find_loopback_device()

    def _find_loopback_device(self):
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
        except OSError:
            raise RuntimeError("WASAPI not available on this system.")

        default_speakers = self.p.get_device_info_by_index(
            wasapi_info["defaultOutputDevice"]
        )

        self.loopback_device = None
        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if dev.get("name", "").startswith(default_speakers["name"]) and dev.get("isLoopbackDevice", False):
                self.loopback_device = dev
                break

        if self.loopback_device is None:
            raise RuntimeError("Could not find a WASAPI loopback device.")

        self.sample_rate = int(self.loopback_device["defaultSampleRate"])
        self.channels = int(self.loopback_device["maxInputChannels"])

    def start(self):
        self.running = True
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.loopback_device["index"],
            frames_per_buffer=self.chunk_size,
            stream_callback=self._callback,
        )
        self.stream.start_stream()

        # Background thread for Windows volume
        self._vol_thread = threading.Thread(target=self._poll_system_volume, daemon=True)
        self._vol_thread.start()

    def _poll_system_volume(self):
        """Poll actual Windows system master volume using pycaw."""
        try:
            from comtypes import CoInitialize, CoUninitialize
            CoInitialize()
            try:
                from pycaw.pycaw import AudioUtilities
                speakers = AudioUtilities.GetSpeakers()
                endpoint_volume = speakers.EndpointVolume

                while self.running:
                    try:
                        vol = endpoint_volume.GetMasterVolumeLevelScalar()
                        with self.lock:
                            self._sys_volume = vol
                    except Exception:
                        pass
                    time.sleep(0.5)
            finally:
                CoUninitialize()
        except Exception:
            pass

    def _callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)

        if self.channels > 1:
            data = data.reshape(-1, self.channels)
            data = np.mean(data, axis=1)

        if len(data) >= self.chunk_size:
            data = data[:self.chunk_size]
        else:
            data = np.pad(data, (0, self.chunk_size - len(data)))

        with self.lock:
            self.audio_data = data.copy()

        return (None, pyaudio.paContinue)

    def get_audio_data(self):
        with self.lock:
            return self.audio_data.copy(), self._sys_volume

    def get_fft(self, num_bars=32):
        data, _ = self.get_audio_data()

        window = np.hanning(len(data))
        windowed = data * window
        fft_data = np.abs(np.fft.rfft(windowed))

        useful_bins = len(fft_data) // 2
        fft_data = fft_data[:useful_bins]

        if len(fft_data) == 0:
            return np.zeros(num_bars)

        bands = np.zeros(num_bars)
        freq_indices = np.logspace(
            np.log10(2), np.log10(len(fft_data) - 1), num_bars + 1, dtype=int
        )

        for i in range(num_bars):
            start = freq_indices[i]
            end = max(freq_indices[i + 1], start + 1)
            bands[i] = np.mean(fft_data[start:end])

        max_val = np.max(bands)
        if max_val > 0:
            bands = bands / max_val

        return bands

    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
