"""
Class ID → name mapping table (Treeview with inline editing, CSV and
YOLO classes.txt import/export). Shared by the converter main window
and the annotator's class editing dialog.
"""

import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import lang
from ui_theme import FG_ACCENT


class ClassManagerFrame(ttk.LabelFrame):
    """Class ID → name mapping table.

    Class IDs are stable: deleting a row never renumbers the remaining ones
    (YOLO class IDs inside .txt files are fixed). IDs without a row fall
    back to default names (class_N) at conversion time, so the generated
    default mapping can be used as-is without any manual editing.
    """

    def __init__(self, parent, settings, **kw):
        super().__init__(parent, **kw)
        self._settings = settings

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=8, pady=(4, 0))

        self._btn_add = ttk.Button(ctrl_frame, command=self._add_row)
        self._btn_add.pack(side=tk.LEFT, padx=2)
        self._btn_remove = ttk.Button(ctrl_frame, command=self._remove_row)
        self._btn_remove.pack(side=tk.LEFT, padx=2)
        self._lbl_count = ttk.Label(ctrl_frame, foreground=FG_ACCENT)
        self._lbl_count.pack(side=tk.RIGHT, padx=4)

        gen_frame = ttk.Frame(self)
        gen_frame.pack(fill=tk.X, padx=8, pady=(2, 0))
        self._lbl_gen_count = ttk.Label(gen_frame)
        self._lbl_gen_count.pack(side=tk.LEFT)
        self._spin_count = ttk.Spinbox(gen_frame, from_=1, to=999, width=5)
        self._spin_count.set("5")
        self._spin_count.pack(side=tk.LEFT, padx=(4, 10))
        self._btn_gen = ttk.Button(gen_frame, command=self._generate_defaults)
        self._btn_gen.pack(side=tk.LEFT, padx=2)

        io_frame = ttk.Frame(self)
        io_frame.pack(fill=tk.X, padx=8, pady=(2, 0))
        self._btn_import = ttk.Button(io_frame, command=self._import_csv)
        self._btn_import.pack(side=tk.LEFT, padx=2)
        self._btn_export = ttk.Button(io_frame, command=self._export_csv)
        self._btn_export.pack(side=tk.LEFT, padx=2)
        self._btn_import_txt = ttk.Button(io_frame, command=self._import_classes_txt)
        self._btn_import_txt.pack(side=tk.LEFT, padx=2)
        self._btn_export_txt = ttk.Button(io_frame, command=self._export_classes_txt)
        self._btn_export_txt.pack(side=tk.LEFT, padx=2)

        self._tree = ttk.Treeview(self, columns=("cid", "name"), show="headings",
                                   height=5, selectmode="browse")
        self._tree.column("cid", width=70, anchor="center")
        self._tree.column("name", width=200)

        self._tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._tree.bind("<Double-1>", self._on_double_click)
        self._restore()
        self._refresh_texts()

    def _refresh_texts(self):
        self.configure(text=lang.tr('class_mapping'))
        self._tree.heading("cid", text=lang.tr('class_col_id'))
        self._tree.heading("name", text=lang.tr('class_col_name'))
        self._btn_add.configure(text=lang.tr('class_add'))
        self._btn_remove.configure(text=lang.tr('class_remove'))
        self._lbl_gen_count.configure(text=lang.tr('class_gen_count'))
        self._btn_gen.configure(text=lang.tr('class_gen'))
        self._btn_import.configure(text=lang.tr('class_import_csv'))
        self._btn_export.configure(text=lang.tr('class_export_csv'))
        self._btn_import_txt.configure(text=lang.tr('class_import_txt'))
        self._btn_export_txt.configure(text=lang.tr('class_export_txt'))
        self._update_count()

    def _add_row(self):
        cid = self._next_cid()
        self._tree.insert("", tk.END, values=(cid, lang.tr('class_default_name', n=cid)))
        self._update_count()

    def _remove_row(self):
        sel = self._tree.selection()
        if sel:
            self._tree.delete(sel[0])
            self._update_count()

    def _next_cid(self):
        cids = []
        for iid in self._tree.get_children():
            try:
                cids.append(int(self._tree.set(iid, "cid")))
            except (TypeError, ValueError):
                continue
        return (max(cids) + 1) if cids else 0

    def _on_double_click(self, event):
        region = self._tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)
        item = self._tree.identify_row(event.y)
        if not item or col != "#2":
            return

        x, y, w, h = self._tree.bbox(item, col)
        old_val = self._tree.set(item, col)

        entry = ttk.Entry(self._tree)
        entry.insert(0, old_val)
        entry.select_range(0, tk.END)
        entry.place(x=x - 2, y=y - 2, width=w + 4, height=h + 4)

        def save(event=None):
            new_val = entry.get().strip()
            if new_val:
                self._tree.set(item, col, new_val)
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)
        entry.focus_set()

    def set_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self._btn_add, self._btn_remove, self._btn_gen,
                    self._btn_import, self._btn_export,
                    self._btn_import_txt, self._btn_export_txt):
            btn.configure(state=state)
        self._spin_count.configure(state=state)

    def _update_count(self):
        n = len(self._tree.get_children())
        self._lbl_count.configure(text=lang.tr('class_count', n=n))
        if n == 0:
            self._add_row()

    def _clear_rows(self):
        for iid in self._tree.get_children():
            self._tree.delete(iid)

    def get_class_mapping(self):
        mapping = {}
        for iid in self._tree.get_children():
            try:
                cid = int(self._tree.set(iid, "cid"))
            except (TypeError, ValueError):
                continue
            mapping[cid] = self._tree.set(iid, "name")
        return mapping

    def get_class_list(self):
        """Dense list of names indexed by class ID; missing IDs get default names."""
        mapping = self.get_class_mapping()
        if not mapping:
            return []
        size = max(mapping) + 1
        return [mapping.get(i, lang.tr('class_default_name', n=i)) for i in range(size)]

    def set_class_list(self, names):
        """Replace the table with a dense 0..n-1 name list (annotator path)."""
        self._clear_rows()
        for i, name in enumerate(names):
            self._tree.insert("", tk.END, values=(i, name))
        self._spin_count.set(str(len(names)))
        self._update_count()

    def save_to_settings(self):
        self._settings.class_names = {
            str(cid): name for cid, name in self.get_class_mapping().items()
        }

    def _restore(self):
        self._clear_rows()
        mapping = self._settings.class_names
        for cid in sorted((k for k in mapping if str(k).isdigit()), key=int):
            self._tree.insert("", tk.END, values=(cid, mapping[cid]))
        self._update_count()

    def _generate_defaults(self):
        try:
            n = int(self._spin_count.get())
        except (TypeError, ValueError):
            return
        n = max(1, min(n, 999))
        if self._tree.get_children() and not messagebox.askyesno(
                lang.tr('class_gen_title'),
                lang.tr('class_gen_confirm', n=n, n1=n - 1)):
            return
        self._clear_rows()
        for i in range(n):
            self._tree.insert("", tk.END, values=(i, lang.tr('class_default_name', n=i)))
        self._update_count()

    def _import_csv(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[(lang.tr('csv_filter'), "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                rows = list(csv.reader(f))
        except Exception as e:
            messagebox.showerror(lang.tr('import_error'), lang.tr('import_failed_msg', e=e))
            return

        seen = set()
        entries = []
        skipped = 0
        for row_data in rows:
            if len(row_data) < 2:
                continue
            cid_raw = row_data[0].strip()
            name = row_data[1].strip()
            if not cid_raw.isdigit() or not name or cid_raw in seen:
                skipped += 1
                continue
            seen.add(cid_raw)
            entries.append((cid_raw, name))

        if not entries:
            messagebox.showwarning(lang.tr('class_mapping'), lang.tr('import_no_rows'))
            return
        self._clear_rows()
        for cid, name in sorted(entries, key=lambda e: int(e[0])):
            self._tree.insert("", tk.END, values=(cid, name))
        self._update_count()
        if skipped:
            messagebox.showinfo(lang.tr('class_mapping'),
                                lang.tr('import_dup_skipped', n=skipped))

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".csv",
            filetypes=[(lang.tr('csv_filter'), "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for cid, name in sorted(self.get_class_mapping().items()):
                    writer.writerow([cid, name])
        except Exception as e:
            messagebox.showerror(lang.tr('export_error'), lang.tr('export_failed_msg', e=e))

    def _read_classes_txt(self, path):
        from yolo_annotation import load_classes_txt
        return load_classes_txt(path)

    def _import_classes_txt(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[(lang.tr('classes_txt_filter'), "*.txt"),
                       (lang.tr('all_files'), "*.*")]
        )
        if not path:
            return
        try:
            names = self._read_classes_txt(path)
        except Exception as e:
            messagebox.showerror(lang.tr('import_error'), lang.tr('import_failed_msg', e=e))
            return
        if not names:
            messagebox.showwarning(lang.tr('class_mapping'), lang.tr('classes_txt_empty'))
            return
        if self._tree.get_children() and not messagebox.askyesno(
                lang.tr('class_mapping'),
                lang.tr('classes_replace_confirm', n=len(names))):
            return
        self.set_class_list(names)

    def _export_classes_txt(self):
        names = self.get_class_list()
        if not names:
            messagebox.showwarning(lang.tr('class_mapping'), lang.tr('classes_txt_empty'))
            return
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            defaultextension=".txt", initialfile="classes.txt",
            filetypes=[(lang.tr('classes_txt_filter'), "*.txt"),
                       (lang.tr('all_files'), "*.*")]
        )
        if not path:
            return
        try:
            from yolo_annotation import save_classes_txt
            save_classes_txt(path, names)
        except Exception as e:
            messagebox.showerror(lang.tr('export_error'), lang.tr('export_failed_msg', e=e))
