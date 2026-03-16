"""
media_info.py — Retrieves currently playing media info from Windows.
Uses the winrt Windows.Media.Control API (GlobalSystemMediaTransportControls)
to detect what song is playing in ANY app (Spotify, Chrome, VLC, etc.)
"""

import asyncio
import threading
import time

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    )

    WINRT_AVAILABLE = True
except ImportError:
    WINRT_AVAILABLE = False


class MediaInfo:
    def __init__(self):
        self.title = "No media detected"
        self.artist = ""
        self.source_app = ""
        self.lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        """Start polling for media info in a background thread."""
        if not WINRT_AVAILABLE:
            with self.lock:
                self.title = "Media detection unavailable (winrt not installed)"
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        """Polling loop that runs in a background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self._running:
            try:
                info = loop.run_until_complete(self._get_media_info_async())
                with self.lock:
                    if info:
                        self.title = info.get("title", "Unknown Title")
                        self.artist = info.get("artist", "Unknown Artist")
                        self.source_app = info.get("source", "")
                    else:
                        self.title = "No media playing"
                        self.artist = ""
                        self.source_app = ""
            except Exception:
                with self.lock:
                    self.title = "No media playing"
                    self.artist = ""
                    self.source_app = ""

            time.sleep(2)  # Poll every 2 seconds

        loop.close()

    async def _get_media_info_async(self):
        """Async function to get current media session info."""
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()

            if session is None:
                return None

            info = await session.try_get_media_properties_async()
            source = session.source_app_user_model_id or ""

            # Clean up source app name
            source_clean = source
            if "!" in source_clean:
                source_clean = source_clean.split("!")[-1]
            if "\\" in source_clean:
                source_clean = source_clean.split("\\")[-1]
            source_clean = source_clean.replace(".exe", "")
            # Capitalize nicely
            known_apps = {
                "spotify": "Spotify",
                "chrome": "Chrome",
                "firefox": "Firefox",
                "msedge": "Edge",
                "vlc": "VLC",
                "brave": "Brave",
                "opera": "Opera",
                "itunes": "iTunes",
                "musicbee": "MusicBee",
                "foobar2000": "foobar2000",
                "winamp": "Winamp",
                "groove": "Groove Music",
            }
            source_lower = source_clean.lower()
            for key, display in known_apps.items():
                if key in source_lower:
                    source_clean = display
                    break
            else:
                source_clean = source_clean.title()

            return {
                "title": info.title or "Unknown Title",
                "artist": info.artist or "Unknown Artist",
                "source": source_clean,
            }
        except Exception:
            return None

    def get_info(self):
        """Return the latest media info."""
        with self.lock:
            return {
                "title": self.title,
                "artist": self.artist,
                "source": self.source_app,
            }

    def get_display_string(self):
        """Return a formatted string for display."""
        with self.lock:
            if self.artist and self.artist != "Unknown Artist":
                text = f"{self.artist} - {self.title}"
            else:
                text = self.title

            if self.source_app:
                text += f"  [{self.source_app}]"

            return text

    def stop(self):
        """Stop the polling thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
