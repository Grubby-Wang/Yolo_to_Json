"""
Settings persistence via configparser (INI file in app directory).
No external dependencies — uses stdlib configparser.
"""

import os
import json
import configparser


APP_NAME = "YoloToJson"


class SettingsManager:
    """Wraps configparser with typed accessors and JSON serialization."""

    def __init__(self):
        ini_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
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
        return self.get_str("conflict_action", "overwrite")

    @conflict_action.setter
    def conflict_action(self, value):
        self.set_str("conflict_action", value)

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
