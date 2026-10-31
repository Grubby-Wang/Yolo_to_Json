"""
YoloToJson — YOLO to LabelMe JSON Converter (GUI Application)

tkinter-based GUI. No external dependencies beyond Pillow (for image size).
Supports Chinese/English language switching (default: Chinese).
Build with PyInstaller for a standalone Windows .exe.
"""

import os
import csv
import json
import sys
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

from settings_manager import SettingsManager
from converter_worker import ConversionWorker
from cropper_window import CropWindow
from annotator_window import AnnotatorWindow
from class_manager import ClassManagerFrame
from yolo_to_json import DEFAULT_IMAGE_EXTENSIONS
from ui_theme import (BG_MAIN, BG_PANEL, BG_INPUT, BG_BUTTON, FG_PRIMARY,
                      FG_ACCENT, FG_SUCCESS, FG_WARN, FG_ERROR, ACCENT_BLUE,
                      BORDER, FONT_MONO, FONT_UI, FONT_TITLE, FONT_BTN,
                      LEVEL_COLORS)
import lang


VERSION = "1.3.0.0"


# ──────────────────────────────────────────────
#  Color theme / fonts — shared in ui_theme.py
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
#  Class Manager Panel — shared in class_manager.py
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
#  File Input Panel
# ──────────────────────────────────────────────

class FileInputFrame(ttk.LabelFrame):
    def __init__(self, parent, settings, **kw):
        super().__init__(parent, **kw)
        self._settings = settings

        self._mode = tk.StringVar(value=settings.input_mode)

        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=8, pady=(4, 0))

        self._lbl_mode = ttk.Label(mode_frame)
        self._lbl_mode.pack(side=tk.LEFT)
        self._rb_single = ttk.Radiobutton(mode_frame, variable=self._mode,
                                          value="single", command=self._update_ui)
        self._rb_single.pack(side=tk.LEFT, padx=4)
        self._rb_batch = ttk.Radiobutton(mode_frame, variable=self._mode,
                                         value="batch", command=self._update_ui)
        self._rb_batch.pack(side=tk.LEFT, padx=4)

        self._lbl_source = ttk.Label(self, foreground=FG_PRIMARY)
        self._lbl_source.pack(anchor=tk.W, padx=8, pady=(8, 0))

        src_frame = ttk.Frame(self)
        src_frame.pack(fill=tk.X, padx=8)
        self._txt_input = tk.StringVar()
        self._entry_input = ttk.Entry(src_frame, textvariable=self._txt_input,
                                       state="readonly", foreground=FG_PRIMARY)
        self._entry_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn_input = ttk.Button(src_frame, command=self._browse_input)
        self._btn_input.pack(side=tk.RIGHT, padx=(4, 0))

        self._lbl_image = ttk.Label(self, foreground=FG_PRIMARY)
        self._lbl_image.pack(anchor=tk.W, padx=8, pady=(8, 0))

        img_frame = ttk.Frame(self)
        img_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self._txt_image = tk.StringVar()
        self._entry_image = ttk.Entry(img_frame, textvariable=self._txt_image,
                                       state="readonly", foreground=FG_PRIMARY)
        self._entry_image.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn_image = ttk.Button(img_frame, command=self._browse_image)
        self._btn_image.pack(side=tk.RIGHT, padx=(4, 0))

        self._update_ui()
        self._refresh_texts()

    def _refresh_texts(self):
        self.configure(text=lang.tr('input_config'))
        self._lbl_mode.configure(text=lang.tr('input_mode'))
        self._rb_single.configure(text=lang.tr('mode_single'))
        self._rb_batch.configure(text=lang.tr('mode_batch'))
        self._lbl_source.configure(text=lang.tr('yolo_source'))
        self._btn_input.configure(text=lang.tr('browse'))
        self._lbl_image.configure(text=lang.tr('image_dir'))
        self._btn_image.configure(text=lang.tr('browse'))

    def _update_ui(self):
        pass

    def _browse_input(self):
        if self._mode.get() == "single":
            path = filedialog.askopenfilename(
                initialdir=self._settings.last_input_dir or "",
                filetypes=[
                    (lang.tr('yolo_file_filter'), "*.txt"),
                    (lang.tr('all_files'), "*.*"),
                ]
            )
        else:
            path = filedialog.askdirectory(
                initialdir=self._settings.last_input_dir or "",
                title=lang.tr('select_yolo_folder')
            )
        if path:
            self._txt_input.set(path)
            self._settings.last_input_dir = os.path.dirname(path) if os.path.isfile(path) else path

    def _browse_image(self):
        path = filedialog.askdirectory(
            initialdir=self._settings.last_image_dir or "",
            title=lang.tr('select_image_folder')
        )
        if path:
            self._txt_image.set(path)
            self._settings.last_image_dir = path

    def get_config(self):
        return {
            'mode': self._mode.get(),
            'input_path': self._txt_input.get().strip(),
            'image_folder': self._txt_image.get().strip(),
        }

    def set_enabled(self, enabled):
        state = "readonly" if enabled else "disabled"
        self._entry_input.configure(state=state)
        self._entry_image.configure(state=state)
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    if isinstance(sub, ttk.Radiobutton) or isinstance(sub, ttk.Button):
                        sub.configure(state="normal" if enabled else "disabled")


# ──────────────────────────────────────────────
#  Output Panel
# ──────────────────────────────────────────────

class OutputFrame(ttk.LabelFrame):
    def __init__(self, parent, settings, **kw):
        super().__init__(parent, **kw)
        self._settings = settings

        self._lbl_dir = ttk.Label(self, foreground=FG_PRIMARY)
        self._lbl_dir.pack(anchor=tk.W, padx=8, pady=(8, 0))

        out_frame = ttk.Frame(self)
        out_frame.pack(fill=tk.X, padx=8)
        self._txt_output = tk.StringVar(value=settings.last_output_dir)
        self._entry_output = ttk.Entry(out_frame, textvariable=self._txt_output,
                                        state="readonly", foreground=FG_PRIMARY)
        self._entry_output.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn_output = ttk.Button(out_frame, command=self._browse_output)
        self._btn_output.pack(side=tk.RIGHT, padx=(4, 0))

        conflict_frame = ttk.Frame(self)
        conflict_frame.pack(fill=tk.X, padx=8, pady=(8, 8))
        self._lbl_conflict = ttk.Label(conflict_frame)
        self._lbl_conflict.pack(side=tk.LEFT)
        # Store the canonical value, not the localized display text —
        # comparing display text broke 'skip' whenever the UI language
        # didn't match the string the worker checks against.
        self._conflict_value = settings.conflict_action
        self._cmb_conflict = ttk.Combobox(conflict_frame, state="readonly", width=12)
        self._cmb_conflict.pack(side=tk.LEFT, padx=6)
        self._cmb_conflict.bind("<<ComboboxSelected>>", self._on_conflict_selected)

        self._refresh_texts()

    CONFLICT_KEYS = ('overwrite', 'skip')

    def _on_conflict_selected(self, event=None):
        idx = self._cmb_conflict.current()
        if 0 <= idx < len(self.CONFLICT_KEYS):
            self._conflict_value = self.CONFLICT_KEYS[idx]

    def _refresh_texts(self):
        self.configure(text=lang.tr('output_config'))
        self._lbl_dir.configure(text=lang.tr('output_dir'))
        self._btn_output.configure(text=lang.tr('browse'))
        self._lbl_conflict.configure(text=lang.tr('if_file_exists'))
        self._cmb_conflict.configure(values=[
            lang.tr('conflict_overwrite'),
            lang.tr('conflict_skip'),
        ])
        # Preserve the canonical selection across language switches
        try:
            self._cmb_conflict.current(self.CONFLICT_KEYS.index(self._conflict_value))
        except ValueError:
            self._conflict_value = self.CONFLICT_KEYS[0]
            self._cmb_conflict.current(0)

    def _browse_output(self):
        path = filedialog.askdirectory(
            initialdir=self._settings.last_output_dir or "",
            title=lang.tr('select_output_folder')
        )
        if path:
            self._txt_output.set(path)
            self._settings.last_output_dir = path

    def get_config(self):
        return {
            'output_dir': self._txt_output.get().strip(),
            'conflict_action': self._conflict_value,
        }

    def set_enabled(self, enabled):
        state = "readonly" if enabled else "disabled"
        self._entry_output.configure(state=state)
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for sub in child.winfo_children():
                    if isinstance(sub, ttk.Combobox) or isinstance(sub, ttk.Button):
                        sub.configure(state="readonly" if enabled else "disabled")


# ──────────────────────────────────────────────
#  Conversion Panel
# ──────────────────────────────────────────────

class ConversionFrame(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=(8, 0))

        self._btn_convert = ttk.Button(btn_frame, command=self._on_convert)
        self._btn_convert.pack(side=tk.LEFT, padx=2)

        self._btn_cancel = ttk.Button(btn_frame, command=self._on_cancel, state="disabled")
        self._btn_cancel.pack(side=tk.LEFT, padx=2)

        self._btn_open = ttk.Button(btn_frame, command=self._on_open_output, state="disabled")
        self._btn_open.pack(side=tk.LEFT, padx=2)

        self._progress = ttk.Progressbar(self, mode="determinate", length=100)
        self._progress.pack(fill=tk.X, padx=8, pady=(8, 0))
        self._progress.pack_forget()

        self._lbl_status = ttk.Label(self, foreground=FG_ACCENT)
        self._lbl_status.pack(anchor=tk.W, padx=8, pady=(4, 8))

        self._convert_cb = None
        self._cancel_cb = None
        self._open_output_cb = None
        self._refresh_texts()

    def _refresh_texts(self):
        self.configure(text=lang.tr('conversion'))
        self._btn_convert.configure(text=lang.tr('btn_convert'))
        self._btn_cancel.configure(text=lang.tr('btn_cancel'))
        self._btn_open.configure(text=lang.tr('btn_open_output'))
        self._lbl_status.configure(text=lang.tr('status_ready'))

    def set_convert_callback(self, cb):
        self._convert_cb = cb

    def set_cancel_callback(self, cb):
        self._cancel_cb = cb

    def set_open_output_callback(self, cb):
        self._open_output_cb = cb

    def _on_convert(self):
        if self._convert_cb:
            self._convert_cb()

    def _on_cancel(self):
        if self._cancel_cb:
            self._cancel_cb()

    def _on_open_output(self):
        if self._open_output_cb:
            self._open_output_cb()

    def set_busy(self):
        self._btn_convert.configure(state="disabled")
        self._btn_cancel.configure(state="normal")
        self._btn_open.configure(state="disabled")
        self._progress.pack(fill=tk.X, padx=8, pady=(8, 0))
        self._progress.configure(value=0, maximum=100)
        self._lbl_status.configure(text=lang.tr('status_converting'), foreground=FG_ACCENT)

    def set_idle(self):
        self._btn_convert.configure(state="normal")
        self._btn_cancel.configure(state="disabled")
        self._btn_open.configure(state="disabled")
        self._progress.pack_forget()
        self._lbl_status.configure(text=lang.tr('status_ready'), foreground=FG_ACCENT)

    def set_completed(self, success, total):
        self._btn_convert.configure(state="normal")
        self._btn_cancel.configure(state="disabled")
        self._btn_open.configure(state="normal")
        self._lbl_status.configure(
            text=lang.tr('status_completed', success=success, total=total),
            foreground=FG_SUCCESS)

    def set_canceled(self, success, total):
        self._btn_convert.configure(state="normal")
        self._btn_cancel.configure(state="disabled")
        self._btn_open.configure(state="normal")
        self._progress.pack_forget()
        self._lbl_status.configure(
            text=lang.tr('status_canceled', success=success, total=total),
            foreground=FG_WARN)

    def update_progress(self, current, total):
        self._progress.configure(maximum=total, value=current)
        self._lbl_status.configure(
            text=lang.tr('status_converting_n', current=current, total=total),
            foreground=FG_ACCENT)


# ──────────────────────────────────────────────
#  Log Panel
# ──────────────────────────────────────────────

LEVEL_COLORS = {
    'info':    FG_PRIMARY,
    'success': FG_SUCCESS,
    'warn':    FG_WARN,
    'error':   FG_ERROR,
}

class LogFrame(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)

        self._text = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, state="disabled",
            font=FONT_MONO, bg="#FAFBFC", fg=FG_PRIMARY,
            insertbackground=FG_PRIMARY, relief=tk.FLAT,
            selectbackground=ACCENT_BLUE
        )
        self._text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._btn_clear = ttk.Button(btn_frame, command=self.clear)
        self._btn_clear.pack(side=tk.LEFT, padx=2)
        self._btn_save = ttk.Button(btn_frame, command=self._save)
        self._btn_save.pack(side=tk.LEFT, padx=2)

        for level, color in LEVEL_COLORS.items():
            self._text.tag_config(level, foreground=color)

        self._refresh_texts()

    def _refresh_texts(self):
        self.configure(text=lang.tr('log_panel'))
        self._btn_clear.configure(text=lang.tr('log_clear'))
        self._btn_save.configure(text=lang.tr('log_save'))

    def append(self, level, message):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level.upper()}] {message}\n"

        self._text.configure(state="normal")
        self._text.insert(tk.END, line, level)
        self._text.see(tk.END)
        self._text.configure(state="disabled")

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)
        self._text.configure(state="disabled")

    def _save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[
                (lang.tr('log_save_dialog'), "*.log"),
                (lang.tr('log_txt_filter'), "*.txt"),
            ]
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._text.get("1.0", tk.END))


# ──────────────────────────────────────────────
#  Main Application Window
# ──────────────────────────────────────────────

class YoloToJsonApp:
    def __init__(self):
        self._settings = SettingsManager()
        self._worker = None
        self._callback_queue = queue.Queue()
        self._crop_win = None
        self._annot_win = None

        # Apply saved language (default: Chinese)
        lang.set_language(self._settings.language)
        lang.on_language_change(self._on_language_changed)

        self.root = tk.Tk()
        self.root.geometry(self._settings.window_geometry)
        self.root.minsize(960, 700)
        self.root.configure(bg=BG_MAIN)

        self._setup_style()
        self._build_ui()
        self._setup_menu()
        self._apply_language()

        self.log("info", lang.tr('log_started'))

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_PANEL, foreground=FG_PRIMARY, font=FONT_UI)
        style.configure("TLabelframe", background=BG_PANEL, bordercolor=BORDER,
                        relief=tk.GROOVE, padding=4)
        style.configure("TLabelframe.Label", background=BG_PANEL, foreground=ACCENT_BLUE,
                        font=FONT_TITLE)
        style.configure("TLabel", background=BG_PANEL, foreground=FG_PRIMARY)
        style.configure("TButton", background=BG_BUTTON, foreground=FG_PRIMARY,
                        borderwidth=1, focusthickness=0, padding=(8, 4))
        style.map("TButton",
                  background=[("active", "#E5E7EB"), ("disabled", "#F5F6F8")],
                  foreground=[("disabled", "#9CA3AF")])
        style.configure("TEntry", fieldbackground=BG_INPUT, foreground=FG_PRIMARY,
                        bordercolor=BORDER, padding=4)
        style.configure("TProgressbar", background=ACCENT_BLUE, troughcolor="#E5E7EB",
                        bordercolor=BORDER)
        style.configure("Treeview", background=BG_PANEL, foreground=FG_PRIMARY,
                        fieldbackground=BG_PANEL, bordercolor=BORDER)
        style.configure("Treeview.Heading", background="#E5E7EB", foreground=FG_PRIMARY,
                        font=FONT_TITLE)
        style.map("Treeview",
                  background=[("selected", "#DBEAFE")],
                  foreground=[("selected", FG_PRIMARY)])
        style.configure("TRadiobutton", background=BG_PANEL, foreground=FG_PRIMARY)
        style.map("TRadiobutton",
                  background=[("active", BG_PANEL), ("selected", BG_PANEL)])
        style.configure("TCombobox", fieldbackground=BG_INPUT, foreground=FG_PRIMARY,
                        background=BG_INPUT)
        style.configure("TCombobox", fieldbackground=BG_INPUT, foreground=FG_PRIMARY)
        style.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)])

    def _build_ui(self):
        # Status bar — bottom first
        self._status_var = tk.StringVar(value=lang.tr('statusbar_ready'))
        self._status_lbl = ttk.Label(self.root, textvariable=self._status_var,
                                      foreground=FG_ACCENT, background=BG_MAIN, anchor=tk.W)
        self._status_lbl.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 4))

        # Conversion panel — above status bar
        self._conv_panel = ConversionFrame(self.root)
        self._conv_panel.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 2))
        self._conv_panel.set_convert_callback(self._start_conversion)
        self._conv_panel.set_cancel_callback(self._cancel_conversion)
        self._conv_panel.set_open_output_callback(self._open_output_dir)

        # Main content area — grid layout (no sash)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)

        # Left panel
        left = ttk.Frame(main_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 3))

        # Output panel — pinned to bottom of left panel first
        self._output_panel = OutputFrame(left, self._settings)
        self._output_panel.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=2)

        # File input — top
        self._file_panel = FileInputFrame(left, self._settings)
        self._file_panel.pack(fill=tk.X, padx=2, pady=2)

        # Class manager — fills remaining middle space
        self._class_panel = ClassManagerFrame(left, self._settings)
        self._class_panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Right panel (log)
        right = ttk.Frame(main_frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

        self._log_panel = LogFrame(right)
        self._log_panel.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _setup_menu(self):
        self._menubar = tk.Menu(self.root, bg=BG_PANEL, fg=FG_PRIMARY,
                                 activebackground=ACCENT_BLUE, activeforeground="white",
                                 font=FONT_UI, tearoff=0)
        self.root.configure(menu=self._menubar)

        self._menu_file = tk.Menu(self._menubar, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                                   activebackground=ACCENT_BLUE)
        self._menu_file.add_command(command=self._on_close, accelerator="Alt+F4")
        self._menubar.add_cascade(menu=self._menu_file)

        self._menu_tools = tk.Menu(self._menubar, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                                    activebackground=ACCENT_BLUE)
        self._menu_tools.add_command(command=self._open_cropper)
        self._menu_tools.add_command(command=self._open_annotator)
        self._menubar.add_cascade(menu=self._menu_tools)

        self._menu_view = tk.Menu(self._menubar, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                                   activebackground=ACCENT_BLUE)
        self._menu_view.add_command(command=self._log_panel.clear)
        self._menubar.add_cascade(menu=self._menu_view)

        self._menu_lang = tk.Menu(self._menubar, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                                   activebackground=ACCENT_BLUE)
        self._menu_lang.add_command(label="中文", command=lambda: self._switch_language('zh'))
        self._menu_lang.add_command(label="English", command=lambda: self._switch_language('en'))
        self._menubar.add_cascade(menu=self._menu_lang)

        self._menu_help = tk.Menu(self._menubar, tearoff=0, bg=BG_PANEL, fg=FG_PRIMARY,
                                   activebackground=ACCENT_BLUE)
        self._menu_help.add_command(command=self._about)
        self._menubar.add_cascade(menu=self._menu_help)

    def _switch_language(self, code):
        lang.set_language(code)
        self._settings.language = code

    def _on_language_changed(self, code):
        self._apply_language()

    def _apply_language(self):
        self.root.title(lang.tr('app_title') + f" v{VERSION}")
        self._status_var.set(lang.tr('statusbar_ready'))

        # Rebuild menus (need to tear down and recreate)
        self._menubar.delete(0, tk.END)
        self._menu_file.delete(0, tk.END)
        self._menu_tools.delete(0, tk.END)
        self._menu_view.delete(0, tk.END)
        self._menu_lang.delete(0, tk.END)
        self._menu_help.delete(0, tk.END)

        self._menu_file.add_command(label=lang.tr('menu_exit'),
                                     command=self._on_close, accelerator="Alt+F4")
        self._menubar.add_cascade(label=lang.tr('menu_file'), menu=self._menu_file)

        self._menu_tools.add_command(label=lang.tr('menu_crop_tool'),
                                      command=self._open_cropper)
        self._menu_tools.add_command(label=lang.tr('menu_annot_tool'),
                                      command=self._open_annotator)
        self._menubar.add_cascade(label=lang.tr('menu_tools'), menu=self._menu_tools)

        self._menu_view.add_command(label=lang.tr('menu_clear_log'),
                                     command=self._log_panel.clear)
        self._menubar.add_cascade(label=lang.tr('menu_view'), menu=self._menu_view)

        self._menu_lang.add_command(label=lang.tr('lang_zh'),
                                     command=lambda: self._switch_language('zh'))
        self._menu_lang.add_command(label=lang.tr('lang_en'),
                                     command=lambda: self._switch_language('en'))
        self._menubar.add_cascade(label=lang.tr('menu_language'), menu=self._menu_lang)

        self._menu_help.add_command(label=lang.tr('menu_about'), command=self._about)
        self._menubar.add_cascade(label=lang.tr('menu_help'), menu=self._menu_help)

        # Refresh all GUI panels
        self._file_panel._refresh_texts()
        self._class_panel._refresh_texts()
        self._output_panel._refresh_texts()
        self._conv_panel._refresh_texts()
        self._log_panel._refresh_texts()

    # ── Conversion lifecycle ──

    def _start_conversion(self):
        config = self._gather_config()
        errors = self._validate(config)
        if errors:
            messagebox.showwarning(lang.tr('val_title'), "\n".join(errors))
            return

        self.log("info", lang.tr('log_starting_convert'))
        self._conv_panel.set_busy()
        self._file_panel.set_enabled(False)
        self._class_panel.set_enabled(False)
        self._output_panel.set_enabled(False)
        self._status_var.set(lang.tr('statusbar_converting'))

        self._last_result = None
        self._last_error = None

        self._worker = ConversionWorker(
            config,
            on_progress=self._on_progress,
            on_log=self._on_log,
            on_finished=self._on_finished,
            on_error=self._on_error,
        )
        self._worker.start()
        self.root.after(100, self._tick_worker)

    def _cancel_conversion(self):
        if self._worker:
            self._worker.cancel()
            self.log("warn", lang.tr('log_cancel_req'))
            self._status_var.set(lang.tr('statusbar_canceling'))

    def _tick_worker(self):
        # Drain progress/log callbacks onto main thread
        while not self._callback_queue.empty():
            try:
                cb = self._callback_queue.get_nowait()
                cb()
            except queue.Empty:
                break

        if not self._worker or not self._worker.is_running():
            self._finish_conversion()
            return

        self.root.after(100, self._tick_worker)

    def _finish_conversion(self):
        # Drain any remaining callbacks
        while not self._callback_queue.empty():
            try:
                cb = self._callback_queue.get_nowait()
                cb()
            except queue.Empty:
                break

        # Reset ALL panels to enabled — called on main thread, guaranteed
        self._conv_panel.set_idle()
        self._file_panel.set_enabled(True)
        self._class_panel.set_enabled(True)
        self._output_panel.set_enabled(True)

        if self._last_error:
            self._conv_panel.set_idle()
            self.log("error", self._last_error)
            self._status_var.set(lang.tr('statusbar_error'))
            messagebox.showerror(lang.tr('error_title'), self._last_error)
        elif self._last_result:
            r = self._last_result
            if r.get('canceled'):
                done = (r.get('success', 0) + r.get('failed', 0)
                        + r.get('skipped', 0))
                self._conv_panel.set_canceled(r.get('success', 0), r.get('total', 0))
                self.log("warn",
                    lang.tr('log_canceled',
                        success=r.get('success', 0),
                        failed=r.get('failed', 0),
                        skipped=r.get('skipped', 0),
                        done=done,
                        total=r.get('total', 0)))
                self._status_var.set(lang.tr('statusbar_canceled',
                    success=r.get('success', 0), total=r.get('total', 0)))
            else:
                self._conv_panel.set_completed(r.get('success', 0), r.get('total', 0))
                self.log("info",
                    lang.tr('log_complete',
                        success=r.get('success', 0),
                        failed=r.get('failed', 0),
                        skipped=r.get('skipped', 0)))
                self._status_var.set(lang.tr('statusbar_done',
                    success=r.get('success', 0), total=r.get('total', 0)))
                errors = r.get('errors', [])
                if errors:
                    messagebox.showinfo(
                        lang.tr('complete_title'),
                        lang.tr('complete_msg',
                            success=r.get('success', 0),
                            failed=r.get('failed', 0),
                            skipped=r.get('skipped', 0),
                            nerr=len(errors)))
        else:
            self._conv_panel.set_idle()
            self._status_var.set(lang.tr('statusbar_ready'))

        self._worker = None
        self._save_settings()

    def _on_progress(self, current, total):
        self._callback_queue.put(lambda c=current, t=total: self._conv_panel.update_progress(c, t))

    def _on_finished(self, result):
        self._last_result = result

    def _on_error(self, message):
        self._last_error = message

    def _on_log(self, level, message):
        self._callback_queue.put(lambda l=level, m=message: self._log_panel.append(l, m))

    # ── Helpers ──

    def _gather_config(self):
        return {
            'mode': self._file_panel.get_config()['mode'],
            'input_path': self._file_panel.get_config()['input_path'],
            'image_folder': self._file_panel.get_config()['image_folder'],
            'output_dir': self._output_panel.get_config()['output_dir'],
            'conflict_action': self._output_panel.get_config()['conflict_action'],
            'class_list': self._class_panel.get_class_list(),
            'extensions': DEFAULT_IMAGE_EXTENSIONS,
        }

    def _validate(self, config):
        errors = []
        if not config['input_path']:
            errors.append(lang.tr('val_select_file_or_folder'))
        elif not os.path.exists(config['input_path']):
            errors.append(lang.tr('val_input_not_exist', path=config['input_path']))
        if not config['output_dir']:
            errors.append(lang.tr('val_specify_output'))
        if not config['image_folder']:
            errors.append(lang.tr('val_specify_image'))
        elif not os.path.exists(config['image_folder']):
            errors.append(lang.tr('val_image_not_exist', path=config['image_folder']))
        if not config['class_list']:
            errors.append(lang.tr('val_define_class'))
        return errors

    def _save_settings(self):
        self._class_panel.save_to_settings()
        fc = self._file_panel.get_config()
        oc = self._output_panel.get_config()
        self._settings.input_mode = fc['mode']
        if fc['input_path']:
            if os.path.isfile(fc['input_path']):
                self._settings.last_input_dir = os.path.dirname(fc['input_path'])
            else:
                self._settings.last_input_dir = fc['input_path']
        self._settings.last_image_dir = fc['image_folder']
        self._settings.last_output_dir = oc['output_dir']
        self._settings.conflict_action = oc['conflict_action']

    def log(self, level, message):
        self._log_panel.append(level, message)

    def _open_output_dir(self):
        out_dir = self._output_panel.get_config().get('output_dir', '')
        if out_dir and os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            messagebox.showwarning(lang.tr('val_title'), lang.tr('val_specify_output'))

    def _open_cropper(self):
        """Singleton crop tool window: re-raise if already open."""
        if self._crop_win is not None and self._crop_win.winfo_exists():
            self._crop_win.deiconify()
            self._crop_win.lift()
            self._crop_win.focus_set()
        else:
            self._crop_win = CropWindow(self.root, self._settings)

    def _open_annotator(self):
        """Singleton YOLO annotation window: re-raise if already open."""
        if self._annot_win is not None and self._annot_win.winfo_exists():
            self._annot_win.deiconify()
            self._annot_win.lift()
            self._annot_win.focus_set()
        else:
            self._annot_win = AnnotatorWindow(self.root, self._settings)

    def _about(self):
        messagebox.showinfo(lang.tr('about_title'), lang.tr('about_text', version=VERSION))

    def _on_close(self):
        self._save_settings()
        self._settings.window_geometry = self.root.winfo_geometry()
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

def main():
    app = YoloToJsonApp()
    app.run()


if __name__ == "__main__":
    main()
