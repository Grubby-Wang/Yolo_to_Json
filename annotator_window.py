"""
YOLO Annotation Tool window (Toplevel).

Full box editing on the shared viewer base: draw / select / move / 8-handle
resize / delete / reassign class, undo-redo per image, a synchronized box
list, wheel zoom + middle-drag pan, and per-image YOLO .txt persistence
with optional auto-save on navigation.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import lang
from viewer_base import ImageViewerBase
from ui_theme import BOX_PALETTE, FG_ACCENT, FG_SUCCESS, FG_WARN, FG_ERROR
from yolo_annotation import (parse_yolo_txt, write_yolo_txt,
                             load_classes_txt, save_classes_txt,
                             label_path_for)
from class_manager import ClassManagerFrame
from image_cropper import Region

HANDLE = 6          # half-size of resize handles, canvas px
MIN_BOX_PX = 3      # minimum box size, image px


def _copy_boxes(boxes):
    return [Region(b.x, b.y, b.w, b.h, b.label) for b in boxes]


def _boxes_sig(boxes):
    return tuple((b.x, b.y, b.w, b.h, b.label) for b in boxes)


class AnnotatorViewer(ImageViewerBase):
    """Canvas with full rectangle-annotation editing (image-px math)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, enable_zoom_pan=True, **kw)
        self.boxes = []                # list[Region], label = class_id str
        self.selected = None           # index into boxes
        self.current_class_id = 0
        self.get_class_names = lambda: []   # injected by the window
        self.on_boxes_changed = None   # callable()
        self.on_selection_changed = None    # callable()

        self._mode = None              # 'draw' | 'move' | 'resize'
        self._drag_start = None        # image-px anchor
        self._drag_rect = None         # preview while drawing
        self._drag_idx = None
        self._handle = None
        self._gesture_orig = None      # undo snapshot taken at gesture start
        self._undo_stack = []
        self._redo_stack = []

        self.canvas.bind("<ButtonPress-3>", self._on_right_press)

    # ── Public API ──

    def set_boxes(self, boxes):
        self.boxes = _copy_boxes(boxes)
        self.selected = None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._cancel_gesture()
        self._render()
        self._notify_selection()

    def get_boxes(self):
        return _copy_boxes(self.boxes)

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(_copy_boxes(self.boxes))
        self.boxes = self._undo_stack.pop()
        self.selected = None
        self._render()
        self._notify_change()
        self._notify_selection()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(_copy_boxes(self.boxes))
        self.boxes = self._redo_stack.pop()
        self.selected = None
        self._render()
        self._notify_change()
        self._notify_selection()

    @property
    def can_undo(self):
        return bool(self._undo_stack)

    @property
    def can_redo(self):
        return bool(self._redo_stack)

    def delete_selected(self):
        if self.selected is None or not (0 <= self.selected < len(self.boxes)):
            return
        self._begin_gesture()
        del self.boxes[self.selected]
        self.selected = None
        self._commit_gesture()

    def set_class_of_selected(self, cid):
        if self.selected is None or not (0 <= self.selected < len(self.boxes)):
            return
        b = self.boxes[self.selected]
        if b.label == str(cid):
            return
        self._begin_gesture()
        b.label = str(cid)
        self._commit_gesture()

    # ── Gesture plumbing ──

    def _begin_gesture(self):
        self._gesture_orig = _copy_boxes(self.boxes)

    def _commit_gesture(self):
        orig = self._gesture_orig
        self._gesture_orig = None
        self._cancel_gesture()
        if orig is not None and _boxes_sig(orig) != _boxes_sig(self.boxes):
            self._undo_stack.append(orig)
            if len(self._undo_stack) > 100:
                self._undo_stack.pop(0)
            self._redo_stack.clear()
            self._render()
            self._notify_change()
        else:
            self._render()

    def _cancel_gesture(self):
        self._mode = None
        self._drag_start = None
        self._drag_rect = None
        self._drag_idx = None
        self._handle = None

    def _notify_change(self):
        if self.on_boxes_changed:
            self.on_boxes_changed()

    def _notify_selection(self):
        if self.on_selection_changed:
            self.on_selection_changed(self.selected)

    # ── Hit testing (image px) ──

    def _box_px(self, i):
        iw, ih = self.image_size()
        return self.boxes[i].to_pixels(iw, ih)  # (px, py, pw, ph)

    def _handle_points(self, px):
        x0, y0, x1, y1 = px[0], px[1], px[0] + px[2], px[1] + px[3]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return {'nw': (x0, y0), 'n': (mx, y0), 'ne': (x1, y0), 'e': (x1, my),
                'se': (x1, y1), 's': (mx, y1), 'sw': (x0, y1), 'w': (x0, my)}

    def _handle_at(self, ix, iy):
        if self.selected is None:
            return None
        r = HANDLE / self._scale + 2 / self._scale
        px = self._box_px(self.selected)
        x0, y0, x1, y1 = px[0], px[1], px[0] + px[2], px[1] + px[3]
        for name, (hx, hy) in self._handle_points(px).items():
            # edge handles only meaningful when the edge can move
            if abs(ix - hx) <= r and abs(iy - hy) <= r:
                if name == 'n' and (y1 - y0) < 4 * r:
                    continue
                if name == 's' and (y1 - y0) < 4 * r:
                    continue
                if name == 'e' and (x1 - x0) < 4 * r:
                    continue
                if name == 'w' and (x1 - x0) < 4 * r:
                    continue
                return name
        return None

    def _box_at(self, ix, iy):
        r = 2 / self._scale
        for i in range(len(self.boxes) - 1, -1, -1):
            bx0, by0, bw, bh = self._box_px(i)
            bx1, by1 = bx0 + bw, by0 + bh
            if bx0 - r <= ix <= bx1 + r and by0 - r <= iy <= by1 + r:
                return i
        return None

    # ── Left-button editing ──

    def _clamp_pt(self, ix, iy):
        iw, ih = self.image_size()
        return max(0, min(ix, iw)), max(0, min(iy, ih))

    def on_draw_start(self, ix, iy):
        if self._pil is None:
            return
        ix, iy = self._clamp_pt(ix, iy)
        h = self._handle_at(ix, iy)
        if h:
            self._mode = 'resize'
            self._handle = h
            self._drag_idx = self.selected
            self._begin_gesture()
            return
        b = self._box_at(ix, iy)
        if b is not None:
            self._mode = 'move'
            self._drag_idx = b
            self.selected = b
            self._drag_start = (ix, iy)
            self._begin_gesture()
            self._render()
            self._notify_selection()
            return
        self._mode = 'draw'
        self._drag_start = (ix, iy)
        self._drag_rect = (ix, iy, ix, iy)
        if self.selected is not None:
            self.selected = None
            self._notify_selection()
        self._begin_gesture()

    def on_draw_move(self, ix, iy):
        if not self._mode:
            return
        ix, iy = self._clamp_pt(ix, iy)
        if self._mode == 'draw':
            x0, y0 = self._drag_start
            self._drag_rect = (min(x0, ix), min(y0, iy), max(x0, ix), max(y0, iy))
        elif self._mode == 'move':
            iw, ih = self.image_size()
            b = self.boxes[self._drag_idx]
            bx0, by0, bw, bh = b.to_pixels(iw, ih)
            dx = ix - self._drag_start[0]
            dy = iy - self._drag_start[1]
            dx = max(-bx0, min(dx, iw - (bx0 + bw)))
            dy = max(-by0, min(dy, ih - (by0 + bh)))
            self.boxes[self._drag_idx] = Region.from_pixels(
                bx0 + dx, by0 + dy, bw, bh, iw, ih, b.label)
        elif self._mode == 'resize':
            self._resize_to(ix, iy)
        self._render()

    def _resize_to(self, ix, iy):
        iw, ih = self.image_size()
        b = self.boxes[self._drag_idx]
        x0, y0, bw, bh = b.to_pixels(iw, ih)
        x1, y1 = x0 + bw, y0 + bh
        h = self._handle
        if 'w' in h:
            x0 = max(0, min(ix, x1 - MIN_BOX_PX))
        if 'e' in h:
            x1 = max(x0 + MIN_BOX_PX, min(ix, iw))
        if 'n' in h:
            y0 = max(0, min(iy, y1 - MIN_BOX_PX))
        if 's' in h:
            y1 = max(y0 + MIN_BOX_PX, min(iy, ih))
        self.boxes[self._drag_idx] = Region.from_pixels(
            x0, y0, x1 - x0, y1 - y0, iw, ih, b.label)

    def on_draw_end(self, ix, iy):
        if not self._mode:
            return
        ix, iy = self._clamp_pt(ix, iy)
        if self._mode == 'draw':
            rect = self._drag_rect
            pw = rect[2] - rect[0]
            ph = rect[3] - rect[1]
            if pw >= MIN_BOX_PX and ph >= MIN_BOX_PX:
                iw, ih = self.image_size()
                self.boxes.append(Region.from_pixels(
                    rect[0], rect[1], pw, ph, iw, ih, str(self.current_class_id)))
                self.selected = len(self.boxes) - 1
                self._commit_gesture()
                self._notify_selection()
            else:
                # accidental click: discard gesture, keep prior state
                orig = self._gesture_orig
                self._gesture_orig = None
                self._cancel_gesture()
                if orig is not None:
                    self.boxes = orig
                    self._render()
        elif self._mode == 'move':
            self._commit_gesture()
        elif self._mode == 'resize':
            self._commit_gesture()

    # ── Right-click menu ──

    def _on_right_press(self, event):
        if self._pil is None:
            return
        ix, iy = self.canvas_to_image(event.x, event.y)
        idx = self._box_at(ix, iy)
        if idx is None:
            return
        self.selected = idx
        self._render()
        self._notify_selection()

        menu = tk.Menu(self, tearoff=0)
        class_menu = tk.Menu(menu, tearoff=0)
        for cid, name in enumerate(self.get_class_names()):
            class_menu.add_command(
                label=f"{cid}  {name}",
                command=lambda c=cid: self.set_class_of_selected(c))
        menu.add_cascade(label=lang.tr('annot_change_class'), menu=class_menu)
        menu.add_command(label=lang.tr('annot_delete_box'),
                         command=self.delete_selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ── Overlay rendering ──

    def _render_overlay(self):
        names = self.get_class_names()
        for i, b in enumerate(self.boxes):
            try:
                cid = int(b.label)
            except (TypeError, ValueError):
                cid = -1
            color = BOX_PALETTE[cid % len(BOX_PALETTE)] if cid >= 0 else "#888888"
            px, py, pw, ph = self._box_px(i)
            x0, y0 = self.image_to_canvas(px, py)
            x1, y1 = self.image_to_canvas(px + pw, py + ph)
            sel = (i == self.selected)
            self.canvas.create_rectangle(
                x0, y0, x1, y1, outline=color,
                width=3 if sel else 2, tags=("overlay",))
            label = f"{cid} {names[cid]}" if 0 <= cid < len(names) else str(cid)
            if y0 >= 16:
                self.canvas.create_text(
                    x0 + 1, y0 - 3, text=label, fill=color,
                    anchor="sw", font=("Segoe UI", 9, "bold"), tags=("overlay",))
            else:
                self.canvas.create_text(
                    x0 + 1, y0 + 3, text=label, fill=color,
                    anchor="nw", font=("Segoe UI", 9, "bold"), tags=("overlay",))
            if sel:
                for hx, hy in self._handle_points((px, py, px + pw, py + ph)).values():
                    cx, cy = self.image_to_canvas(hx, hy)
                    self.canvas.create_rectangle(
                        cx - HANDLE, cy - HANDLE, cx + HANDLE, cy + HANDLE,
                        fill="white", outline=color, width=1, tags=("overlay",))
        if self._drag_rect:
            x0, y0 = self.image_to_canvas(self._drag_rect[0], self._drag_rect[1])
            x1, y1 = self.image_to_canvas(self._drag_rect[2], self._drag_rect[3])
            self.canvas.create_rectangle(
                x0, y0, x1, y1, outline="#FFFFFF", width=1,
                dash=(4, 3), tags=("overlay",))


class ClassListShim:
    """Minimal settings-like object for ClassManagerFrame inside dialogs."""

    def __init__(self, mapping):
        self.class_names = dict(mapping)


class AnnotatorWindow(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self._settings = settings
        self._dirty = False
        self._classes_dirty = False
        self._class_names = []
        self._current_class = 0

        self.title(f"{lang.tr('annot_tool')} — YoloToJson")
        self.geometry(settings.annot_window_geometry)
        self.minsize(960, 600)
        self.configure(bg="#F0F2F5")

        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──

    def _build_ui(self):
        bar1 = ttk.Frame(self)
        bar1.pack(fill=tk.X, padx=8, pady=(8, 2))
        ttk.Button(bar1, text=lang.tr('crop_open_folder'),
                   command=self._open_folder).pack(side=tk.LEFT, padx=2)
        ttk.Separator(bar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        ttk.Button(bar1, text=lang.tr('crop_prev'), width=7,
                   command=self._nav_prev).pack(side=tk.LEFT, padx=2)
        self._lbl_counter = ttk.Label(bar1, text="-", foreground=FG_ACCENT)
        self._lbl_counter.pack(side=tk.LEFT, padx=6)
        ttk.Button(bar1, text=lang.tr('crop_next'), width=7,
                   command=self._nav_next).pack(side=tk.LEFT, padx=2)
        ttk.Label(bar1, text=lang.tr('crop_goto')).pack(side=tk.LEFT, padx=(10, 2))
        self._spin_goto = ttk.Spinbox(bar1, from_=1, to=1, width=5)
        self._spin_goto.pack(side=tk.LEFT)
        self._spin_goto.bind("<Return>", self._on_goto)

        ttk.Separator(bar1, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self._btn_undo = ttk.Button(bar1, text=lang.tr('annot_undo'), width=6,
                                    command=self._undo, state="disabled")
        self._btn_undo.pack(side=tk.LEFT, padx=2)
        self._btn_redo = ttk.Button(bar1, text=lang.tr('annot_redo'), width=6,
                                    command=self._redo, state="disabled")
        self._btn_redo.pack(side=tk.LEFT, padx=2)
        ttk.Button(bar1, text=lang.tr('annot_copy_prev'),
                   command=self._copy_prev).pack(side=tk.LEFT, padx=2)

        self._auto_save_var = tk.BooleanVar(value=self._settings.annot_auto_save)
        ttk.Checkbutton(bar1, text=lang.tr('crop_auto_save'),
                        variable=self._auto_save_var,
                        command=self._persist_auto_save).pack(side=tk.RIGHT, padx=4)
        self._btn_save = ttk.Button(bar1, text=lang.tr('annot_save'),
                                    command=self._save, state="disabled")
        self._btn_save.pack(side=tk.RIGHT, padx=2)

        bar2 = ttk.Frame(self)
        bar2.pack(fill=tk.X, padx=8, pady=(2, 4))
        ttk.Label(bar2, text=lang.tr('annot_current_class')).pack(side=tk.LEFT, padx=2)
        self._cmb_class = ttk.Combobox(bar2, state="readonly", width=24)
        self._cmb_class.pack(side=tk.LEFT, padx=4)
        self._cmb_class.bind("<<ComboboxSelected>>", self._on_class_selected)
        ttk.Button(bar2, text=lang.tr('annot_edit_classes'),
                   command=self._edit_classes).pack(side=tk.LEFT, padx=2)
        ttk.Label(bar2, text=lang.tr('annot_hint'), foreground="#6B7280").pack(
            side=tk.LEFT, padx=10)

        # Viewer + box list
        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, padx=8)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self._viewer = AnnotatorViewer(body)
        self._viewer.grid(row=0, column=0, sticky="nsew")
        self._viewer.on_boxes_changed = self._on_boxes_changed
        self._viewer.on_selection_changed = self._on_selection_changed
        self._viewer.on_image_changed = self._on_image_changed
        self._viewer.get_class_names = lambda: self._class_names

        side = ttk.LabelFrame(body, text=lang.tr('annot_box_list'))
        side.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        self._tree = ttk.Treeview(side, columns=("num", "cls", "geo"),
                                  show="headings", height=18,
                                  selectmode="browse")
        self._tree.heading("num", text="#")
        self._tree.heading("cls", text=lang.tr('class_col_name'))
        self._tree.heading("geo", text=lang.tr('annot_col_geo'))
        self._tree.column("num", width=36, anchor="center", stretch=False)
        self._tree.column("cls", width=90)
        self._tree.column("geo", width=120)
        self._tree.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self._tree.bind("<<TreeviewSelect>>", self._on_list_select)
        ttk.Button(side, text=lang.tr('annot_delete_box'),
                   command=self._delete_selected).pack(fill=tk.X, padx=4, pady=(0, 4))

        # Status bar
        self._status_var = tk.StringVar(value=lang.tr('status_ready'))
        self._status_lbl = ttk.Label(self, textvariable=self._status_var,
                                     foreground=FG_ACCENT, anchor=tk.W)
        self._status_lbl.pack(fill=tk.X, padx=8, pady=(2, 4))

    def _bind_keys(self):
        self.bind("<Left>", lambda e: self._nav_prev())
        self.bind("<Right>", lambda e: self._nav_next())
        self.bind("<Escape>", self._deselect)
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Control-s>", lambda e: self._save())
        for d in "0123456789":
            self.bind(d, lambda e, n=int(d): self._on_digit(n))
        self._viewer.canvas.bind("<Left>", lambda e: self._nav_prev())
        self._viewer.canvas.bind("<Right>", lambda e: self._nav_next())
        self._viewer.canvas.bind("<Escape>", self._deselect)
        self._viewer.canvas.bind("<Delete>", lambda e: self._delete_selected())

    # ── Class management ──

    def _set_class_names(self, names):
        self._class_names = [n for n in names if n]
        if not self._class_names:
            self._class_names = [lang.tr('class_default_name', n=0)]
        values = [f"{i}  {n}" for i, n in enumerate(self._class_names)]
        self._cmb_class.configure(values=values)
        self._current_class = min(self._current_class, len(self._class_names) - 1)
        self._cmb_class.current(self._current_class)
        self._viewer.current_class_id = self._current_class

    def _on_class_selected(self, event=None):
        idx = self._cmb_class.current()
        if idx >= 0:
            self._current_class = idx
            self._viewer.current_class_id = idx

    def _on_digit(self, n):
        if n < len(self._class_names):
            self._current_class = n
            self._cmb_class.current(n)
            self._viewer.current_class_id = n
            self._viewer.set_class_of_selected(n)

    def _edit_classes(self):
        mapping = {str(i): n for i, n in enumerate(self._class_names)}
        shim = ClassListShim(mapping)
        dlg = tk.Toplevel(self)
        dlg.title(lang.tr('annot_edit_classes'))
        dlg.transient(self)
        dlg.grab_set()
        frame = ClassManagerFrame(dlg, shim)
        frame.pack(fill=tk.BOTH, expand=True)
        dlg.geometry(f"420x420+{self.winfo_rootx() + 80}+{self.winfo_rooty() + 60}")

        def close():
            names = frame.get_class_list()
            if names != self._class_names:
                self._set_class_names(names)
                self._classes_dirty = True
                self._refresh_box_list()
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", close)
        ttk.Button(dlg, text=lang.tr('crop_confirm_btn_save'),
                   command=close).pack(pady=6)
        self.wait_window(dlg)

    # ── Folder open / navigation ──

    def _open_folder(self):
        path = filedialog.askdirectory(title=lang.tr('select_folder_title'))
        if not path:
            return
        classes_path = os.path.join(path, "classes.txt")
        if os.path.exists(classes_path):
            self._set_class_names(load_classes_txt(classes_path))
            self._classes_dirty = False
        else:
            mapping = self._settings.class_names
            self._set_class_names([mapping[str(i)] for i in sorted(
                (int(k) for k in mapping if str(k).isdigit()))] or [])
        self._folder = path
        self._viewer.load_folder(path)
        if not self._viewer.count:
            messagebox.showwarning(lang.tr('annot_tool'),
                                   lang.tr('log_no_txt', path=path), parent=self)
        self._btn_save.configure(state="normal")

    def _check_dirty_before_nav(self):
        """True = proceed; False = stay. Auto-saves or asks first."""
        if not self._dirty:
            return True
        if self._auto_save_var.get():
            self._save(silent=True)
            return True
        ans = messagebox.askyesnocancel(
            lang.tr('annot_tool'), lang.tr('annot_unsaved_prompt'), parent=self)
        if ans is None:
            return False
        if ans:
            self._save(silent=True)
        else:
            self._dirty = False
        return True

    def _nav_prev(self):
        if self._check_dirty_before_nav():
            self._viewer.prev_image()

    def _nav_next(self):
        if self._check_dirty_before_nav():
            self._viewer.next_image()

    def _on_goto(self, event=None):
        try:
            i = int(self._spin_goto.get())
        except ValueError:
            return
        if self._check_dirty_before_nav():
            self._viewer.goto_index(i - 1)

    def _on_image_changed(self, index, path):
        total = self._viewer.count
        self._lbl_counter.configure(text=f"{index + 1}/{total}")
        self._spin_goto.configure(to=max(1, total))
        self._spin_goto.set(str(index + 1))
        self._viewer.set_boxes(parse_yolo_txt(label_path_for(path)))
        self._dirty = False
        self._refresh_box_list()
        self._update_status()

    # ── Box edits / list sync ──

    def _on_boxes_changed(self):
        self._dirty = True
        self._refresh_box_list()
        self._update_status()
        self._update_undo_buttons()

    def _on_selection_changed(self, idx):
        if idx is None:
            self._tree.selection_remove(self._tree.selection())
        else:
            iid = str(idx)
            if self._tree.exists(iid):
                self._tree.selection_set(iid)
                self._tree.see(iid)
        self._update_status()

    def _on_list_select(self, event=None):
        sel = self._tree.selection()
        if sel and sel[0].isdigit():
            idx = int(sel[0])
            if 0 <= idx < len(self._viewer.boxes):
                self._viewer.selected = idx
                self._viewer._render()

    def _refresh_box_list(self):
        self._tree.delete(*self._tree.get_children())
        for i, b in enumerate(self._viewer.boxes):
            try:
                cid = int(b.label)
                name = self._class_names[cid] if cid < len(self._class_names) else str(cid)
            except (TypeError, ValueError):
                name = str(b.label)
            self._tree.insert("", tk.END, iid=str(i),
                              values=(i + 1, name,
                                      f"{b.x:.3f},{b.y:.3f} {b.w:.3f}×{b.h:.3f}"))

    def _delete_selected(self):
        self._viewer.delete_selected()

    def _deselect(self, event=None):
        self._viewer.selected = None
        self._viewer._render()
        self._viewer._notify_selection()

    def _undo(self):
        self._viewer.undo()

    def _redo(self):
        self._viewer.redo()

    def _update_undo_buttons(self):
        self._btn_undo.configure(state="normal" if self._viewer.can_undo else "disabled")
        self._btn_redo.configure(state="normal" if self._viewer.can_redo else "disabled")

    def _copy_prev(self):
        idx = self._viewer.index
        if idx <= 0 or not self._viewer.count:
            return
        prev_boxes = parse_yolo_txt(
            label_path_for(self._viewer.files[idx - 1]))
        self._viewer.set_boxes(prev_boxes)
        self._dirty = True
        self._refresh_box_list()
        self._update_status()

    # ── Save / status ──

    def _save(self, silent=False):
        path = self._viewer.current_path
        if not path:
            return
        if not write_yolo_txt(label_path_for(path), self._viewer.boxes):
            if not silent:
                messagebox.showerror(lang.tr('annot_tool'),
                                     lang.tr('crop_failed', base=os.path.basename(path)),
                                     parent=self)
            return
        if self._classes_dirty:
            folder = os.path.dirname(path)
            save_classes_txt(os.path.join(folder, "classes.txt"), self._class_names)
            self._classes_dirty = False
        self._dirty = False
        self._update_status()
        if not silent:
            self._status_var.set(lang.tr('crop_status_save',
                                 path=label_path_for(path)))

    def _update_status(self):
        path = self._viewer.current_path
        if not path:
            self._status_var.set(lang.tr('status_ready'))
            return
        iw, ih = self._viewer.image_size()
        n = len(self._viewer.boxes)
        zoom = self._viewer.zoom_level
        state = lang.tr('annot_unsaved') if self._dirty else lang.tr('annot_saved')
        color = FG_WARN if self._dirty else FG_SUCCESS
        self._status_var.set(
            lang.tr('annot_status', w=iw, h=ih, zoom=f"{zoom * 100:.0f}",
                    n=n, state=state))
        self._status_lbl.configure(foreground=color)

    # ── Persistence / close ──

    def _persist_auto_save(self):
        self._settings.annot_auto_save = self._auto_save_var.get()

    def _on_close(self):
        if self._dirty and not self._auto_save_var.get():
            ans = messagebox.askyesnocancel(
                lang.tr('annot_tool'), lang.tr('annot_unsaved_prompt'), parent=self)
            if ans is None:
                return
            if ans:
                self._save(silent=True)
        elif self._dirty:
            self._save(silent=True)
        self._settings.annot_window_geometry = self.winfo_geometry()
        self._persist_auto_save()
        self.destroy()
