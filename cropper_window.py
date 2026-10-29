"""
Image Cropping Tool window (Toplevel).

Opened from the main window's Tools menu. Built on ImageViewerBase so a
future YOLO annotation window can reuse the same browsing/coordinate
infrastructure. Batch cropping runs in a background thread with callbacks
drained onto the UI thread via .after() polling (same pattern as the
converter).
"""

import os
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

import lang
from viewer_base import ImageViewerBase
from image_cropper import Region, batch_crop, crop_image, make_crop_path

RECT_COLOR = "#FF3B30"
LEVEL_COLORS = {'info': "#1F2937", 'success': "#059669",
                'warn': "#D97706", 'error': "#DC2626"}
CONFLICT_KEYS = ('overwrite', 'skip')


class CropperViewer(ImageViewerBase):
    """Viewer with a rubber-band crop rectangle (normalized Region)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.region = None            # finalized Region (normalized)
        self.on_region_changed = None  # callable(region or None)
        self._drag_start = None       # image-px anchor while dragging
        self._drag_rect = None        # (ix0, iy0, ix1, iy1) while dragging

    # Rubber-band handlers (image-pixel coords from the base class)

    def on_draw_start(self, ix, iy):
        iw, ih = self.image_size()
        if iw and ih:
            self._drag_start = (max(0, min(ix, iw)), max(0, min(iy, ih)))

    def on_draw_move(self, ix, iy):
        if not self._drag_start:
            return
        iw, ih = self.image_size()
        cx = max(0, min(ix, iw))
        cy = max(0, min(iy, ih))
        x0, y0 = self._drag_start
        self._drag_rect = (min(x0, cx), min(y0, cy),
                           max(x0, cx), max(y0, cy))
        self._redraw_overlay()
        self._notify_preview(self._drag_rect)

    def on_draw_end(self, ix, iy):
        start = self._drag_start
        if start is None:
            return
        iw, ih = self.image_size()
        cx = max(0, min(ix, iw))
        cy = max(0, min(iy, ih))
        rect = self._drag_rect
        if rect is None:  # press+release without a move event
            x0, y0 = start
            rect = (min(x0, cx), min(y0, cy), max(x0, cx), max(y0, cy))
        self._drag_start = None
        self._drag_rect = None
        px, py, pw, ph = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
        if pw < 3 or ph < 3:            # accidental click → drop any old rect
            self.clear_rect()
            return
        self.region = Region.from_pixels(px, py, pw, ph, iw, ih)
        self._redraw_overlay()
        if self.on_region_changed:
            self.on_region_changed(self.region)

    def _notify_preview(self, rect):
        if self.on_region_changed:
            self.on_region_changed(
                Region.from_pixels(rect[0], rect[1],
                                   rect[2] - rect[0], rect[3] - rect[1],
                                   *self.image_size()),
                preview=True)

    def clear_rect(self):
        self.region = None
        self._drag_start = None
        self._drag_rect = None
        self._redraw_overlay()
        if self.on_region_changed:
            self.on_region_changed(None)

    def _redraw_overlay(self):
        self.clear_overlay()
        rect = self._drag_rect
        if rect is None and self.region is not None:
            iw, ih = self.image_size()
            px, py, pw, ph = self.region.to_pixels(iw, ih)
            rect = (px, py, px + pw, py + ph)
        if rect:
            x0, y0 = self.image_to_canvas(rect[0], rect[1])
            x1, y1 = self.image_to_canvas(rect[2], rect[3])
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=RECT_COLOR,
                                         width=2, tags=("overlay",))

    def _render_overlay(self):
        self._redraw_overlay()


class SaveCropDialog(tk.Toplevel):
    """Modal 3-choice dialog: save to session dir / change folder / cancel.

    result: ('save', None) | ('other', chosen_dir) | None (cancelled).
    """

    def __init__(self, parent, message, title):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text=message, justify=tk.LEFT, padding=12).pack()
        btns = ttk.Frame(self, padding=(12, 0, 12, 12))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text=lang.tr('crop_confirm_btn_save'),
                   command=lambda: self._done('save')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=lang.tr('crop_confirm_btn_other'),
                   command=self._choose_other).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=lang.tr('crop_confirm_btn_cancel'),
                   command=self.destroy).pack(side=tk.LEFT, padx=2)

        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _done(self, action):
        self.result = (action, None)
        self.destroy()

    def _choose_other(self):
        path = filedialog.askdirectory(parent=self,
                                       title=lang.tr('select_folder_title'))
        if path:
            self.result = ('other', path)
            self.destroy()


class SelectImagesDialog(tk.Toplevel):
    """Modal multi-select list of the loaded images (全选/全不选/反选)."""

    def __init__(self, parent, paths):
        super().__init__(parent)
        self.result = None
        self.title(lang.tr('crop_select_title'))
        self.transient(parent)
        self.grab_set()

        self._tree = ttk.Treeview(self, columns=("name",), show="headings",
                                  height=16, selectmode="extended")
        self._tree.heading("name", text=lang.tr('crop_select_col'))
        self._tree.column("name", width=380)
        self._tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for p in paths:
            self._tree.insert("", tk.END, iid=p, values=(os.path.basename(p),))

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text=lang.tr('crop_select_all'),
                   command=lambda: self._sel('all')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=lang.tr('crop_select_none'),
                   command=lambda: self._sel('none')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=lang.tr('crop_select_invert'),
                   command=lambda: self._sel('invert')).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text=lang.tr('crop_select_ok'),
                   command=self._apply).pack(side=tk.RIGHT, padx=2)
        ttk.Button(btns, text=lang.tr('btn_cancel'),
                   command=self.destroy).pack(side=tk.RIGHT, padx=2)

        self._sel('all')
        self.geometry(f"+{parent.winfo_rootx() + 60}+{parent.winfo_rooty() + 60}")

    def _sel(self, mode):
        kids = self._tree.get_children()
        if mode == 'all':
            self._tree.selection_set(kids)
        elif mode == 'none':
            self._tree.selection_remove(kids)
        else:
            cur = set(self._tree.selection())
            self._tree.selection_remove([k for k in kids if k in cur])
            self._tree.selection_set([k for k in kids if k not in cur])

    def _apply(self):
        self.result = list(self._tree.selection())
        self.destroy()


class BatchCropWorker:
    """Runs batch_crop in a daemon thread; GUI polls a callback queue."""

    def __init__(self, paths, region, output_dir, conflict,
                 on_progress, on_log, on_finished):
        self._paths = paths
        self._region = region
        self._output_dir = output_dir
        self._conflict = conflict
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_finished = on_finished
        self._canceled = False
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._canceled = True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        result = batch_crop(
            self._paths, self._region, output_dir=self._output_dir,
            conflict=self._conflict,
            cancel_check=lambda: self._canceled,
            progress_callback=self.on_progress,
            log_callback=self.on_log,
        )
        self.on_finished(result)


class CropWindow(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self._settings = settings
        self._callback_queue = queue.Queue()
        self._worker = None

        self.title(f"{lang.tr('crop_tool')} — YoloToJson")
        self.geometry(settings.crop_window_geometry)
        self.minsize(860, 560)
        self.configure(bg="#F0F2F5")

        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log('info', lang.tr('log_started'))

    # ── UI construction ──

    def _build_ui(self):
        # Toolbar row 1: open / navigate / auto-save
        bar1 = ttk.Frame(self)
        bar1.pack(fill=tk.X, padx=8, pady=(8, 2))

        ttk.Button(bar1, text=lang.tr('crop_open_folder'),
                   command=self._open_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar1, text=lang.tr('crop_open_files'),
                   command=self._open_files).pack(side=tk.LEFT, padx=2)
        ttk.Separator(bar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(bar1, text=lang.tr('crop_prev'), width=7,
                   command=self._viewer_prev).pack(side=tk.LEFT, padx=2)
        self._lbl_counter = ttk.Label(bar1, text="-", foreground="#2563EB")
        self._lbl_counter.pack(side=tk.LEFT, padx=6)
        ttk.Button(bar1, text=lang.tr('crop_next'), width=7,
                   command=self._viewer_next).pack(side=tk.LEFT, padx=2)
        ttk.Label(bar1, text=lang.tr('crop_goto')).pack(side=tk.LEFT, padx=(10, 2))
        self._spin_goto = ttk.Spinbox(bar1, from_=1, to=1, width=5)
        self._spin_goto.pack(side=tk.LEFT)
        self._spin_goto.bind("<Return>", self._on_goto)

        self._auto_save_var = tk.BooleanVar(value=self._settings.crop_auto_save)
        ttk.Checkbutton(bar1, text=lang.tr('crop_auto_save'),
                        variable=self._auto_save_var,
                        command=self._persist_auto_save).pack(side=tk.RIGHT, padx=4)

        # Toolbar row 2: output target / conflict / batch actions
        bar2 = ttk.Frame(self)
        bar2.pack(fill=tk.X, padx=8, pady=(2, 4))

        self._out_mode = tk.StringVar(value=self._settings.crop_output_mode)
        ttk.Radiobutton(bar2, text=lang.tr('crop_out_source'), value="source",
                        variable=self._out_mode).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(bar2, text=lang.tr('crop_out_custom'), value="custom",
                        variable=self._out_mode).pack(side=tk.LEFT, padx=2)
        self._txt_out_dir = tk.StringVar(value=self._settings.crop_output_dir)
        ttk.Entry(bar2, textvariable=self._txt_out_dir, width=30).pack(
            side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        ttk.Button(bar2, text=lang.tr('browse'), width=7,
                   command=self._browse_out_dir).pack(side=tk.LEFT, padx=2)

        ttk.Label(bar2, text=lang.tr('if_file_exists')).pack(side=tk.LEFT, padx=(10, 2))
        self._cmb_conflict = ttk.Combobox(bar2, state="readonly", width=8)
        self._cmb_conflict['values'] = [lang.tr('conflict_overwrite'),
                                        lang.tr('conflict_skip')]
        self._conflict = self._settings.crop_conflict
        self._cmb_conflict.current(CONFLICT_KEYS.index(self._conflict))
        self._cmb_conflict.pack(side=tk.LEFT, padx=2)
        self._cmb_conflict.bind("<<ComboboxSelected>>", self._on_conflict)

        # Viewer area
        self._viewer = CropperViewer(self)
        self._viewer.pack(fill=tk.BOTH, expand=True, padx=8, pady=2)
        self._viewer.on_region_changed = self._on_region_changed
        self._viewer.on_image_changed = self._on_image_changed

        # Batch action bar
        bar3 = ttk.Frame(self)
        bar3.pack(fill=tk.X, padx=8, pady=(2, 2))
        ttk.Button(bar3, text=lang.tr('crop_btn_apply_all'),
                   command=self._apply_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar3, text=lang.tr('crop_btn_apply_sel'),
                   command=self._apply_selected).pack(side=tk.LEFT, padx=2)
        self._btn_cancel_batch = ttk.Button(bar3, text=lang.tr('btn_cancel'),
                                            command=self._cancel_batch,
                                            state="disabled")
        self._btn_cancel_batch.pack(side=tk.LEFT, padx=2)
        self._lbl_rect = ttk.Label(bar3, foreground="#2563EB")
        self._lbl_rect.pack(side=tk.RIGHT, padx=4)

        # Progress
        self._progress = ttk.Progressbar(self, mode="determinate")
        self._progress.pack(fill=tk.X, padx=8)
        self._progress.pack_forget()

        # Mini log
        self._log_text = scrolledtext.ScrolledText(
            self, height=6, wrap=tk.WORD, state="disabled",
            font=("Consolas", 9), bg="#FAFBFC", fg="#1F2937", relief=tk.FLAT)
        self._log_text.pack(fill=tk.X, padx=8, pady=(2, 8))
        for level, color in LEVEL_COLORS.items():
            self._log_text.tag_config(level, foreground=color)

    def _bind_keys(self):
        self.bind("<Left>", lambda e: self._viewer_prev())
        self.bind("<Right>", lambda e: self._viewer_next())
        self.bind("<Escape>", lambda e: self._viewer.clear_rect())
        self._viewer.canvas.bind("<Left>", lambda e: self._viewer_prev())
        self._viewer.canvas.bind("<Right>", lambda e: self._viewer_next())
        self._viewer.canvas.bind("<Escape>", lambda e: self._viewer.clear_rect())

    # ── File open / navigation ──

    def _open_folder(self):
        path = filedialog.askdirectory(title=lang.tr('select_folder_title'))
        if not path:
            return
        self._viewer.load_folder(path)
        if not self._viewer.count:
            self._log('warn', lang.tr('log_no_txt', path=path))

    def _open_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[(lang.tr('image_filter'), "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                       (lang.tr('all_files'), "*.*")])
        if paths:
            self._viewer.set_files(sorted(paths))

    def _viewer_prev(self):
        self._viewer.prev_image()

    def _viewer_next(self):
        self._viewer.next_image()

    def _on_goto(self, event=None):
        try:
            i = int(self._spin_goto.get())
        except ValueError:
            return
        self._viewer.goto_index(i - 1)

    def _on_image_changed(self, index, path):
        # NOTE: the drawn Region intentionally persists across images —
        # it is normalized, so it stays valid for batch apply while browsing.
        total = self._viewer.count
        self._lbl_counter.configure(text=f"{index + 1}/{total}")
        self._spin_goto.configure(to=max(1, total))
        self._spin_goto.set(str(index + 1))
        self._update_rect_label(self._viewer.region)

    def _update_rect_label(self, region):
        if region is None:
            self._lbl_rect.configure(
                text=f"{lang.tr('crop_rect_lbl')} {lang.tr('crop_rect_none')}")
            return
        iw, ih = self._viewer.image_size()
        px, py, pw, ph = region.to_pixels(iw, ih)
        self._lbl_rect.configure(
            text=f"{lang.tr('crop_rect_lbl')} {px},{py} {pw}×{ph}px")

    def _on_region_changed(self, region, preview=False):
        self._update_rect_label(region)
        if region is not None and not preview:
            self._save_current(region)

    def _resolve_output_dir(self, src_path):
        if self._out_mode.get() == "custom":
            d = self._txt_out_dir.get().strip()
            if d and os.path.isdir(d):
                return d
            self._log('warn', lang.tr('val_image_not_exist', path=d or '?'))
        return os.path.dirname(src_path) or "."

    def _save_current(self, region):
        src = self._viewer.current_path
        if not src:
            messagebox.showwarning(lang.tr('crop_error_title'),
                                   lang.tr('crop_no_image'), parent=self)
            return
        out_dir = self._resolve_output_dir(src)
        dest = make_crop_path(src, output_dir=out_dir)
        iw, ih = self._viewer.image_size()
        px, py, pw, ph = region.to_pixels(iw, ih)

        if not self._auto_save_var.get():
            dlg = SaveCropDialog(
                self,
                lang.tr('crop_confirm_msg', path=dest, w=pw, h=ph),
                lang.tr('crop_confirm_title'))
            self.wait_window(dlg)
            action, new_dir = dlg.result or (None, None)
            if action == 'other' and new_dir:
                self._out_mode.set("custom")
                self._txt_out_dir.set(new_dir)
                self._persist_output()
                dest = make_crop_path(src, output_dir=new_dir)
            elif action != 'save':
                return
        elif os.path.exists(dest) and self._conflict != 'overwrite':
            self._log('warn', lang.tr('crop_skip_exists', base=os.path.basename(src)))
            self._viewer.next_image()
            return

        status = crop_image(src, region, dest,
                            overwrite=(self._conflict == 'overwrite'))
        if status == 'success':
            self._log('success', lang.tr('crop_status_save', path=dest))
        elif status == 'exists':
            self._log('warn', lang.tr('crop_skip_exists', base=os.path.basename(src)))
        else:
            self._log('error', lang.tr('crop_failed', base=os.path.basename(src)))

        if self._viewer.index < self._viewer.count - 1:
            self._viewer.next_image()

    # ── Batch apply ──

    def _apply_all(self):
        self._start_batch(self._viewer.files)

    def _apply_selected(self):
        if not self._viewer.count:
            messagebox.showwarning(lang.tr('crop_error_title'),
                                   lang.tr('crop_no_image'), parent=self)
            return
        dlg = SelectImagesDialog(self, self._viewer.files)
        self.wait_window(dlg)
        if dlg.result:
            self._start_batch(dlg.result)

    def _start_batch(self, paths):
        region = self._viewer.region
        if region is None:
            messagebox.showwarning(lang.tr('crop_error_title'),
                                   lang.tr('crop_no_rect'), parent=self)
            return
        if not paths:
            messagebox.showwarning(lang.tr('crop_error_title'),
                                   lang.tr('crop_no_image'), parent=self)
            return
        out_dir = (self._txt_out_dir.get().strip()
                   if self._out_mode.get() == "custom" and
                   os.path.isdir(self._txt_out_dir.get().strip()) else None)
        if not messagebox.askyesno(lang.tr('crop_batch_title'),
                                   lang.tr('crop_batch_confirm', n=len(paths)),
                                   parent=self):
            return

        self._worker = BatchCropWorker(
            paths, region, out_dir, self._conflict,
            on_progress=lambda c, t: self._callback_queue.put(
                lambda c=c, t=t: self._on_batch_progress(c, t)),
            on_log=lambda l, m: self._callback_queue.put(
                lambda l=l, m=m: self._log(l, m)),
            on_finished=lambda r: self._callback_queue.put(
                lambda r=r: self._on_batch_finished(r)),
        )
        self._worker.start()
        self._progress.pack(fill=tk.X, padx=8, pady=2)
        self._progress.configure(value=0, maximum=len(paths))
        self._btn_cancel_batch.configure(state="normal")
        self.after(100, self._tick_worker)

    def _tick_worker(self):
        while not self._callback_queue.empty():
            try:
                cb = self._callback_queue.get_nowait()
                cb()
            except queue.Empty:
                break
        if self._worker and not self._worker.is_running():
            self._finish_batch()
        elif self._worker:
            self.after(100, self._tick_worker)

    def _on_batch_progress(self, current, total):
        self._progress.configure(maximum=total, value=current)

    def _on_batch_finished(self, r):
        done = r['success'] + r['failed'] + r['skipped']
        if r['canceled']:
            self._log('warn', lang.tr('crop_batch_canceled',
                      success=r['success'], failed=r['failed'],
                      skipped=r['skipped'], done=done, total=r['total']))
        else:
            self._log('info', lang.tr('crop_batch_done',
                      success=r['success'], failed=r['failed'],
                      skipped=r['skipped'], total=r['total']))
            if r['errors']:
                messagebox.showinfo(lang.tr('crop_batch_title'),
                                    "\n".join(r['errors'][:10]), parent=self)
        self._last_batch_result = r

    def _finish_batch(self):
        self._progress.pack_forget()
        self._btn_cancel_batch.configure(state="disabled")
        self._worker = None

    def _cancel_batch(self):
        if self._worker:
            self._worker.cancel()
            self._log('warn', lang.tr('log_cancel_req'))

    # ── Settings / persistence ──

    def _on_conflict(self, event=None):
        idx = self._cmb_conflict.current()
        if 0 <= idx < len(CONFLICT_KEYS):
            self._conflict = CONFLICT_KEYS[idx]
            self._settings.set_str("conflict_action", self._conflict)

    def _persist_auto_save(self):
        self._settings.crop_auto_save = self._auto_save_var.get()

    def _persist_output(self):
        self._settings.crop_output_mode = self._out_mode.get()
        self._settings.crop_output_dir = self._txt_out_dir.get().strip()

    def _browse_out_dir(self):
        path = filedialog.askdirectory(
            initialdir=self._txt_out_dir.get() or "",
            title=lang.tr('select_output_folder'))
        if path:
            self._txt_out_dir.set(path)
            self._out_mode.set("custom")
            self._persist_output()

    # ── Log ──

    def _log(self, level, message):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.configure(state="normal")
        self._log_text.insert(tk.END, f"[{ts}] [{level.upper()}] {message}\n", level)
        self._log_text.see(tk.END)
        self._log_text.configure(state="disabled")

    # ── Close ──

    def _on_close(self):
        if self._worker and self._worker.is_running():
            self._worker.cancel()
        self._settings.crop_window_geometry = self.winfo_geometry()
        self._persist_auto_save()
        self._persist_output()
        self.destroy()
