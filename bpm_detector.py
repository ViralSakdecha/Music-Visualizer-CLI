"""
bpm_detector.py — Real-time BPM estimation using spectral flux / energy difference.
"""

import numpy as np
import threading
import time
from collections import deque

class BPMDetector:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.bpm = 0.0
        self.lock = threading.Lock()

        # We will poll 30 times a second. Need a 4-5 second history to find tempo.
        self.history_size = int(30 * 4) 
        self.flux_history = deque(maxlen=self.history_size)
        self.prev_spectrum = None
        
        # Smooth resulting BPM
        self._bpm_history = deque(maxlen=15)

    def process(self, audio_data):
        # Window the data
        window = np.hanning(len(audio_data))
        spectrum = np.abs(np.fft.rfft(audio_data * window))
        
        # Calculate spectral flux (positive change in energy)
        if self.prev_spectrum is not None:
            diff = spectrum - self.prev_spectrum
            
            # Sum positive differences (onset energy)
            pos_diff = np.where(diff > 0, diff, 0)
            flux = np.sum(pos_diff)
            
            self.flux_history.append(flux)
            
        self.prev_spectrum = spectrum

        # We only want to analyze BPM when we have a full buffer
        if len(self.flux_history) < self.history_size // 2:
            return

        flux_arr = np.array(self.flux_history)
        
        # Normalize
        flux_arr -= np.mean(flux_arr)
        std = np.std(flux_arr)
        if std < 1e-10:
            return
            
        flux_arr /= std

        # Autocorrelation (measuring similarity when delayed)
        n = len(flux_arr)
        fft_flux = np.fft.fft(flux_arr, n=2*n)
        acf = np.fft.ifft(fft_flux * np.conj(fft_flux))[:n].real
        
        if acf[0] == 0:
            return
        acf /= acf[0]

        # Valid lag range based on FPS (assume process is called 30 times a second)
        # e.g. 60 BPM (1 beat / sec) = 30 process calls
        # 180 BPM (3 beat / sec) = 10 process calls
        fps = 30.0 
        min_lag = int(fps * (60.0 / 185.0)) # ~185 BPM max
        max_lag = int(fps * (60.0 / 65.0))  # ~65 BPM min
        
        min_lag = max(1, min_lag)
        max_lag = min(max_lag, n - 1)

        if min_lag >= max_lag:
            return

        search_region = acf[min_lag:max_lag]
        if len(search_region) == 0:
            return

        # Find the lag with maximum similarity
        best_lag = np.argmax(search_region) + min_lag
        
        # Convert lag back to BPM
        current_bpm = (fps * 60.0) / best_lag
        
        with self.lock:
            # Add to history to compute rolling median (ignores spurious jumps)
            self._bpm_history.append(current_bpm)
            median_bpm = np.median(self._bpm_history)
            
            # Snap to integer
            self.bpm = round(median_bpm)

    def get_bpm(self):
        """Return the current BPM estimate."""
        with self.lock:
            return self.bpm
