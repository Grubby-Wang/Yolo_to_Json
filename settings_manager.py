"""
Settings persistence via configparser (INI file in app directory).
No external dependencies — uses stdlib configparser.
"""

import os
import sys
import json
import configparser


APP_NAME = "YoloToJson"


def _app_dir():
    """Directory for config.ini: next to the .exe when frozen (PyInstaller),
    otherwise next to this source file. Writing next to __file__ in a frozen
    onefile exe would target the temporary _MEIxxxx extraction dir."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


class SettingsManager:
    """Wraps configparser with typed accessors and JSON serialization."""

    def __init__(self):
        ini_path = os.path.join(_app_dir(), "config.ini")
        self._path = ini_path
        self._cfg = configparser.ConfigParser()
        self._section = "Settings"
        if os.path.exists(ini_path):
            self._cfg.read(ini_path, encoding='utf-8')
        if not self._cfg.has_section(self._section):
            self._cfg.add_section(self._section)

    def _save(self):
        with open(self._path, 'w', encoding='utf-8') as f:
            self._cfg.write(f)

    def get_str(self, key, default=""):
        return self._cfg.get(self._section, key, fallback=default)

    def set_str(self, key, value):
        self._cfg.set(self._section, key, str(value))
        self._save()

    def get_bool(self, key, default=False):
        return self._cfg.getboolean(self._section, key, fallback=default)

    def set_bool(self, key, value):
        self._cfg.set(self._section, key, str(value).lower())
        self._save()

    def get_json(self, key, default=None):
        if default is None:
            default = {}
        raw = self._cfg.get(self._section, key, fallback=None)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    def set_json(self, key, value):
        self._cfg.set(self._section, key, json.dumps(value))
        self._save()

    # ---- App-specific keys ----

    @property
    def last_input_dir(self):
        return self.get_str("last_input_dir")

    @last_input_dir.setter
    def last_input_dir(self, value):
        self.set_str("last_input_dir", value)

    @property
    def last_image_dir(self):
        return self.get_str("last_image_dir")

    @last_image_dir.setter
    def last_image_dir(self, value):
        self.set_str("last_image_dir", value)

    @property
    def last_output_dir(self):
        return self.get_str("last_output_dir")

    @last_output_dir.setter
    def last_output_dir(self, value):
        self.set_str("last_output_dir", value)

    @property
    def input_mode(self):
        return self.get_str("input_mode", "batch")

    @input_mode.setter
    def input_mode(self, value):
        self.set_str("input_mode", value)

    @property
    def class_names(self):
        return self.get_json("class_names", {"0": "defect"})

    @class_names.setter
    def class_names(self, value):
        self.set_json("class_names", value)

    @property
    def conflict_action(self):
        """Canonical conflict action: 'overwrite' or 'skip'.

        Older builds stored the localized combo text (e.g. '覆盖'/'跳过'),
        so anything unexpected is normalized instead of trusted."""
        val = self.get_str("conflict_action", "overwrite").strip().lower()
        if val in ('overwrite', 'skip'):
            return val
        if val == '跳过':
            return 'skip'
        return 'overwrite'

    @conflict_action.setter
    def conflict_action(self, value):
        val = str(value).strip().lower()
        if val not in ('overwrite', 'skip'):
            val = 'skip' if val == '跳过' else 'overwrite'
        self.set_str("conflict_action", val)

    @property
    def language(self):
        return self.get_str("language", "zh")

    @language.setter
    def language(self, value):
        self.set_str("language", value)

    @property
    def window_geometry(self):
        return self.get_str("window_geometry", "1024x768+100+80")

    @window_geometry.setter
    def window_geometry(self, value):
        self.set_str("window_geometry", value)

    # ---- Crop tool keys ----

    @property
    def crop_auto_save(self):
        return self.get_bool("crop_auto_save", False)

    @crop_auto_save.setter
    def crop_auto_save(self, value):
        self.set_bool("crop_auto_save", value)

    @property
    def crop_output_dir(self):
        return self.get_str("crop_output_dir")

    @crop_output_dir.setter
    def crop_output_dir(self, value):
        self.set_str("crop_output_dir", value)

    @property
    def crop_output_mode(self):
        """'source' (save next to each image) or 'custom'."""
        val = self.get_str("crop_output_mode", "source")
        return val if val in ("source", "custom") else "source"

    @crop_output_mode.setter
    def crop_output_mode(self, value):
        self.set_str("crop_output_mode", value if value in ("source", "custom") else "source")

    @property
    def crop_conflict(self):
        return self.conflict_action  # shared overwrite/skip semantics

    @property
    def crop_window_geometry(self):
        return self.get_str("crop_window_geometry", "1100x720+120+60")

    @crop_window_geometry.setter
    def crop_window_geometry(self, value):
        self.set_str("crop_window_geometry", value)

    # ---- Annotator keys ----

    @property
    def annot_auto_save(self):
        return self.get_bool("annot_auto_save", True)

    @annot_auto_save.setter
    def annot_auto_save(self, value):
        self.set_bool("annot_auto_save", value)

    @property
    def annot_window_geometry(self):
        return self.get_str("annot_window_geometry", "1200x760+100+40")

    @annot_window_geometry.setter
    def annot_window_geometry(self, value):
        self.set_str("annot_window_geometry", value)

    @property
    def delete_remember(self):
        """Image-delete confirmation: remember the user's yes/no choice."""
        return self.get_bool("delete_remember", False)

    @delete_remember.setter
    def delete_remember(self, value):
        self.set_bool("delete_remember", value)

    @property
    def delete_default_yes(self):
        return self.get_bool("delete_default_yes", True)

    @delete_default_yes.setter
    def delete_default_yes(self, value):
        self.set_bool("delete_default_yes", value)
