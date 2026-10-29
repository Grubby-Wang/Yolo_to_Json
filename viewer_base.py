"""
Image Viewer Base — reusable browsing canvas for image tools.

Provides image list navigation, aspect-preserving fit-to-canvas display,
and canvas↔image↔normalized coordinate transforms. Mouse events are
dispatched to overridable on_draw_start/move/end hooks (image-pixel
coordinates), and overlay rendering is a hook — the cropper draws a
rubber-band rectangle, a future YOLO annotator draws labeled boxes on
the same infrastructure.
"""

import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

import lang


CANVAS_BG = "#2B2D31"
CANVAS_FG = "#9CA3AF"


class ImageViewerBase(ttk.Frame):
    """Browse a list of images on a canvas with fit-to-window scaling.

    With enable_zoom_pan=True the base also provides mouse-wheel zoom
    (anchored at the cursor), middle-drag panning and double-click fit
    reset — used by the annotator; the cropper keeps plain fit display.
    """

    MIN_ZOOM = 0.01
    MAX_ZOOM = 64.0

    def __init__(self, parent, enable_zoom_pan=False, **kw):
        super().__init__(parent, **kw)

        self._files = []
        self._index = -1
        self._pil = None          # current PIL image (original size)
        self._photo = None        # keep a reference so tk doesn't GC it
        self._scale = 1.0
        self._fit_scale = 1.0
        self._off_x = 0           # canvas coords of displayed image top-left
        self._off_y = 0
        self._disp_w = 0
        self._disp_h = 0
        self._user_scale = None   # None = fit mode; float = custom zoom
        self._enable_zoom_pan = enable_zoom_pan

        self.on_image_changed = None   # callable(index, path)

        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._hint = None

        self.canvas.bind("<Configure>", lambda e: self._render())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)

        if enable_zoom_pan:
            self.canvas.bind("<MouseWheel>", self._on_wheel)
            self.canvas.bind("<Button-4>", self._on_wheel)      # Linux
            self.canvas.bind("<Button-5>", self._on_wheel)
            self.canvas.bind("<ButtonPress-2>", self._start_pan)
            self.canvas.bind("<B2-Motion>", self._do_pan)
            self.canvas.bind("<Double-Button-1>", self._reset_fit)

    # ── File management ──

    def set_files(self, paths):
        self._files = list(paths)
        if self._files:
            self.goto_index(0)
        else:
            self._clear_image()

    def load_folder(self, folder, extensions=None):
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        allowed = {ext.lower() for ext in extensions}
        try:
            names = os.listdir(folder)
        except OSError:
            names = []
        paths = sorted(os.path.join(folder, n) for n in names
                       if os.path.splitext(n)[1].lower() in allowed)
        self.set_files(paths)

    @property
    def files(self):
        return list(self._files)

    @property
    def current_path(self):
        if 0 <= self._index < len(self._files):
            return self._files[self._index]
        return None

    @property
    def index(self):
        return self._index

    @property
    def count(self):
        return len(self._files)

    # ── Navigation ──

    def next_image(self):
        if self._files:
            self.goto_index(min(self._index + 1, len(self._files) - 1))

    def prev_image(self):
        if self._files:
            self.goto_index(max(self._index - 1, 0))

    def goto_index(self, i):
        if not (0 <= i < len(self._files)):
            return
        self._index = i
        try:
            self._pil = Image.open(self._files[i])
        except Exception:
            self._pil = None
        self._user_scale = None          # new image → back to fit view
        self.clear_overlay()
        self._render()
        if self.on_image_changed:
            self.on_image_changed(i, self._files[i])

    # ── Zoom / pan ──

    @property
    def zoom_level(self):
        return self._scale / self._fit_scale if self._fit_scale else 1.0

    def _on_wheel(self, event):
        if self._pil is None:
            return
        delta = event.delta if hasattr(event, "delta") else 0
        if getattr(event, "num", 0) == 4:
            delta = 120
        elif getattr(event, "num", 0) == 5:
            delta = -120
        factor = 1.2 if delta > 0 else 1 / 1.2
        self.zoom_at(event.x, event.y, factor)

    def zoom_at(self, cx, cy, factor):
        """Scale by `factor` keeping the image point under canvas (cx, cy) fixed."""
        if self._pil is None:
            return
        ix, iy = self.canvas_to_image(cx, cy)
        base = self._user_scale if self._user_scale is not None else self._scale
        new_scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, base * factor))
        self._user_scale = new_scale
        self._scale = new_scale
        self._off_x = cx - ix * new_scale
        self._off_y = cy - iy * new_scale
        self._render()

    def _start_pan(self, event):
        self._pan_from = (event.x, event.y)

    def _do_pan(self, event):
        if not getattr(self, "_pan_from", None) or self._pil is None:
            return
        dx = event.x - self._pan_from[0]
        dy = event.y - self._pan_from[1]
        self._pan_from = (event.x, event.y)
        self._off_x += dx
        self._off_y += dy
        self.canvas.move("all", dx, dy)   # cheap pan; offsets stay in sync

    def _reset_fit(self, event=None):
        self._user_scale = None
        self._render()

    # ── Coordinate transforms ──

    def canvas_to_image(self, cx, cy):
        return ((cx - self._off_x) / self._scale,
                (cy - self._off_y) / self._scale)

    def image_to_canvas(self, ix, iy):
        return (ix * self._scale + self._off_x,
                iy * self._scale + self._off_y)

    def image_size(self):
        if self._pil is not None:
            return self._pil.size
        return (0, 0)

    # ── Mouse dispatch (image-pixel coords) ──

    def _press(self, event):
        if self._pil is None:
            return
        ix, iy = self.canvas_to_image(event.x, event.y)
        self.on_draw_start(ix, iy)

    def _motion(self, event):
        if self._pil is None:
            return
        ix, iy = self.canvas_to_image(event.x, event.y)
        self.on_draw_move(ix, iy)

    def _release(self, event):
        if self._pil is None:
            return
        ix, iy = self.canvas_to_image(event.x, event.y)
        self.on_draw_end(ix, iy)

    def on_draw_start(self, ix, iy):
        pass

    def on_draw_move(self, ix, iy):
        pass

    def on_draw_end(self, ix, iy):
        pass

    # ── Overlay hook ──

    def clear_overlay(self):
        for item in self.canvas.find_withtag("overlay"):
            self.canvas.delete(item)

    def _render(self):
        self.canvas.delete("all")
        self._hint = None
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if self._pil is None or w < 2 or h < 2:
            self._hint = self.canvas.create_text(
                w // 2, h // 2, text=lang.tr('viewer_empty_hint'),
                fill=CANVAS_FG, font=("Segoe UI", 11))
            return

        iw, ih = self._pil.size
        self._fit_scale = min(w / iw, h / ih)
        if self._user_scale is not None:
            self._scale = self._user_scale      # offsets kept as-is (pan/zoom)
        else:
            self._scale = self._fit_scale
            self._off_x = (w - round(iw * self._scale)) // 2
            self._off_y = (h - round(ih * self._scale)) // 2
        self._disp_w = max(1, round(iw * self._scale))
        self._disp_h = max(1, round(ih * self._scale))

        resample = Image.NEAREST if self._scale >= 1 else Image.BILINEAR
        disp = self._pil.resize((self._disp_w, self._disp_h), resample)
        self._photo = ImageTk.PhotoImage(disp)
        self.canvas.create_image(self._off_x, self._off_y,
                                 anchor=tk.NW, image=self._photo)
        self._render_overlay()

    def _render_overlay(self):
        """Subclasses draw rubber bands / boxes here (tagged 'overlay')."""
        pass
