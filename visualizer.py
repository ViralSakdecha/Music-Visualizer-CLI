"""
visualizer.py — Premium minimal ASCII visualizer with curses.
Clean layout, smooth animations, aesthetic design.
"""

import curses
import numpy as np
import math
import time

# ─── Smoothing ───
FALL = 0.12
RISE = 0.85
PEAK_DECAY = 0.02


class Visualizer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.prev_bars = None
        self.peaks = None
        self._t = 0  # animation tick
        self._setup_curses()

    def _setup_curses(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(16)

        curses.start_color()
        curses.use_default_colors()

        #  1 = Green, 2 = Yellow, 3 = Red, 4 = Cyan, 5 = White, 6 = Dim
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        curses.init_pair(5, curses.COLOR_WHITE, -1)
        curses.init_pair(6, 8, -1)  # dim gray

    # ──────────────────── MAIN RENDER ────────────────────
    def render(self, fft_bands, volume, bpm, media_text, elapsed):
        try:
            self.stdscr.erase()
            h, w = self.stdscr.getmaxyx()
            self._t += 1

            if h < 14 or w < 50:
                self._safe(0, 0, "Resize terminal to at least 50x14", curses.color_pair(3))
                self.stdscr.refresh()
                return

            # ─── Layout zones ───
            #  Row 0       : top border
            #  Row 1       : title
            #  Row 2       : now playing
            #  Row 3       : thin separator
            #  Row 4‥h-6   : bars
            #  Row h-5     : floor line
            #  Row h-4     : volume + bpm
            #  Row h-3     : empty
            #  Row h-2     : controls
            #  Row h-1     : bottom border

            bar_top = 4
            bar_bottom = h - 6
            bar_height = bar_bottom - bar_top
            if bar_height < 3:
                bar_height = 3

            bar_w = 2
            gap = 1
            max_bars = (w - 6) // (bar_w + gap)
            num_bars = min(len(fft_bands), max_bars)
            if num_bars <= 0:
                return

            bands = fft_bands[:num_bars]

            # ─── Smooth ───
            if self.prev_bars is None or len(self.prev_bars) != num_bars:
                self.prev_bars = np.zeros(num_bars)
                self.peaks = np.zeros(num_bars)

            for i in range(num_bars):
                t = bands[i]
                if t > self.prev_bars[i]:
                    self.prev_bars[i] += (t - self.prev_bars[i]) * RISE
                else:
                    self.prev_bars[i] += (t - self.prev_bars[i]) * FALL

                if self.prev_bars[i] >= self.peaks[i]:
                    self.peaks[i] = self.prev_bars[i]
                else:
                    self.peaks[i] = max(self.peaks[i] - PEAK_DECAY, 0)

            total_w = num_bars * (bar_w + gap) - gap
            ox = (w - total_w) // 2  # center offset

            # ═══════════ HEADER ═══════════
            self._draw_border_top(w)
            self._draw_title(w)
            self._draw_now_playing(w, media_text)
            # subtle separator
            sep = "·" * (total_w + 4)
            self._safe(3, max(ox - 2, 0), sep, curses.color_pair(6) | curses.A_DIM)

            # ═══════════ BARS ═══════════
            for i in range(num_bars):
                val = self.prev_bars[i]
                pk = self.peaks[i]
                x = ox + i * (bar_w + gap)
                filled = int(val * bar_height)
                peak_row = int(pk * bar_height)

                for row in range(bar_height):
                    y = bar_bottom - row
                    if y < bar_top or y >= h - 1:
                        continue

                    if row < filled:
                        pct = row / bar_height
                        if pct < 0.35:
                            clr = curses.color_pair(1)              # Green
                        elif pct < 0.70:
                            clr = curses.color_pair(2)              # Yellow
                        else:
                            clr = curses.color_pair(3) | curses.A_BOLD  # Red

                        for bw in range(bar_w):
                            self._safe(y, x + bw, "█", clr)
                    elif row == peak_row and peak_row > 0:
                        for bw in range(bar_w):
                            self._safe(y, x + bw, "─", curses.color_pair(5) | curses.A_DIM)

            # floor
            floor_y = bar_bottom + 1
            self._safe(floor_y, ox, "─" * total_w, curses.color_pair(6) | curses.A_DIM)

            # ═══════════ FOOTER ═══════════
            self._draw_footer(w, h, ox, total_w, volume, bpm)

            # ═══════════ BOTTOM BORDER ═══════════
            self._draw_border_bottom(w, h)

            self.stdscr.refresh()
        except curses.error:
            pass

    # ──────────────────── HEADER PARTS ────────────────────

    def _draw_border_top(self, w):
        line = "┌" + "─" * (w - 2) + "┐"
        self._safe(0, 0, line[:w], curses.color_pair(6) | curses.A_DIM)

    def _draw_title(self, w):
        # Animated music note that pulses
        notes = ["♪", "♫", "♪", "♬"]
        note = notes[(self._t // 15) % len(notes)]

        title = f"{note}  A U D I O   V I S U A L I Z E R  {note}"
        cx = (w - len(title)) // 2
        self._safe(1, cx, title, curses.color_pair(4) | curses.A_BOLD)

    def _draw_now_playing(self, w, media_text):
        if len(media_text) > w - 6:
            media_text = media_text[:w - 9] + "..."
        cx = (w - len(media_text)) // 2
        self._safe(2, cx, media_text, curses.color_pair(5))

    # ──────────────────── FOOTER ────────────────────

    def _draw_footer(self, w, h, ox, total_w, volume, bpm):
        row = h - 4

        pct = int(volume * 100)

        # ── Volume section ──
        vol_icon = self._vol_icon(volume)
        vol_label = f" {vol_icon}  VOL "

        # BPM section
        bpm_label = f"  BPM {int(bpm):>3d} " if bpm > 0 else "  BPM --- "
        bpm_dot = "●" if (self._t // 8) % 2 == 0 and bpm > 0 else "○"
        bpm_section = f"{bpm_dot}{bpm_label}"

        # Volume bar occupies space in between
        bar_space = total_w - len(vol_label) - len(bpm_section) - 8
        if bar_space < 5:
            bar_space = 5

        filled_count = int(volume * bar_space)
        empty_count = bar_space - filled_count

        # Build volume bar with gradient
        vol_bar_chars = []
        for j in range(bar_space):
            if j < filled_count:
                ratio = j / bar_space
                if ratio < 0.5:
                    vol_bar_chars.append(("━", curses.color_pair(1)))
                elif ratio < 0.8:
                    vol_bar_chars.append(("━", curses.color_pair(2)))
                else:
                    vol_bar_chars.append(("━", curses.color_pair(3) | curses.A_BOLD))
            else:
                vol_bar_chars.append(("╌", curses.color_pair(6) | curses.A_DIM))

        # Draw volume label
        lx = ox
        self._safe(row, lx, vol_label, curses.color_pair(4))

        # Draw percentage after label
        pct_str = f"{pct:3d}%"
        self._safe(row, lx + len(vol_label), pct_str, curses.color_pair(5) | curses.A_BOLD)

        # Draw bar
        bar_start = lx + len(vol_label) + len(pct_str) + 1
        for j, (ch, clr) in enumerate(vol_bar_chars):
            self._safe(row, bar_start + j, ch, clr)

        # Draw BPM
        bpm_x = bar_start + bar_space + 2
        bpm_color = curses.color_pair(1) if bpm <= 100 else (curses.color_pair(2) if bpm <= 140 else curses.color_pair(3))
        self._safe(row, bpm_x, bpm_section, bpm_color | curses.A_BOLD)

        # Controls
        hint = "[Q] Quit   [+/-] Sensitivity   [R] Reset"
        hx = (w - len(hint)) // 2
        self._safe(h - 2, hx, hint, curses.color_pair(6) | curses.A_DIM)

    def _draw_border_bottom(self, w, h):
        line = "└" + "─" * (w - 2) + "┘"
        self._safe(h - 1, 0, line[:w], curses.color_pair(6) | curses.A_DIM)

    # ──────────────────── HELPERS ────────────────────

    def _vol_icon(self, vol):
        if vol <= 0:
            return "🔇"
        elif vol < 0.33:
            return "🔈"
        elif vol < 0.66:
            return "🔉"
        else:
            return "🔊"

    def _safe(self, y, x, text, attr=0):
        """Safe addstr that never throws."""
        try:
            h, w = self.stdscr.getmaxyx()
            if y < 0 or y >= h or x < 0:
                return
            available = w - x - 1
            if available <= 0:
                return
            self.stdscr.addnstr(y, x, text, available, attr)
        except curses.error:
            pass
