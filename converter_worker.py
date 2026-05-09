"""
Background worker for conversion operations (runs in a thread).
Uses stdlib threading — no Qt dependency.
Calls back to the GUI via a queue polled by tkinter's .after().
"""

import os
import re
import threading

from yolo_to_json import yolo_to_labelme_json, batch_convert_yolo_to_labelme


class ConversionWorker:
    """Runs YOLO→JSON conversion in a background thread.

    Callbacks are called from the worker thread. The GUI polls `self.queue`
    via tkinter's `.after()` to update widgets safely on the main thread.
    """

    def __init__(self, config, on_progress=None, on_log=None, on_finished=None, on_error=None):
        self._config = config
        self._canceled = False

        self.on_progress = on_progress
        self.on_log = on_log
        self.on_finished = on_finished
        self.on_error = on_error

        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        self._canceled = True

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def _emit_progress(self, current, total):
        if self.on_progress and not self._canceled:
            self.on_progress(current, total)

    def _emit_log(self, level, message):
        if self.on_log and not self._canceled:
            self.on_log(level, message)

    def _emit_finished(self, result):
        if self.on_finished:
            self.on_finished(result)

    def _emit_error(self, message):
        if self.on_error:
            self.on_error(message)

    def _run(self):
        mode = self._config.get('mode', 'batch')
        input_path = self._config.get('input_path', '')
        image_folder = self._config.get('image_folder', '')
        output_dir = self._config.get('output_dir', '')
        class_names = self._config.get('class_list', ['object'])
        extensions = self._config.get('extensions', ['.jpg', '.jpeg', '.png', '.bmp'])
        conflict = self._config.get('conflict_action', 'overwrite')

        if self._canceled:
            return

        if not input_path:
            self._emit_error("No input path specified.")
            return

        if not output_dir:
            self._emit_error("No output directory specified.")
            return

        try:
            if mode == 'single':
                self._run_single(input_path, image_folder, output_dir, class_names, conflict)
            else:
                self._run_batch(input_path, image_folder, output_dir, class_names, extensions, conflict)
        except Exception as e:
            self._emit_error(str(e))

    def _run_single(self, yolo_path, image_folder, output_dir, class_names, conflict):
        base_name = os.path.splitext(os.path.basename(yolo_path))[0]

        image_path = None
        if os.path.isfile(image_folder):
            image_path = image_folder
        else:
            extensions = self._config.get('extensions', ['.jpg', '.jpeg', '.png', '.bmp'])
            for ext in extensions:
                for case_ext in (ext, ext.upper()):
                    candidate = os.path.join(image_folder, base_name + case_ext)
                    if os.path.exists(candidate):
                        image_path = candidate
                        break
                if image_path:
                    break

        if image_path is None:
            self._emit_error(f"No matching image found for {base_name}.txt")
            return

        output_json = os.path.join(output_dir, base_name + ".json")

        if os.path.exists(output_json) and conflict == 'skip':
            self._emit_log('warn', f"Skipped {base_name}.txt — output already exists")
            self._emit_finished({'total': 1, 'success': 0, 'failed': 0, 'skipped': 1, 'errors': []})
            return

        os.makedirs(output_dir, exist_ok=True)
        success = yolo_to_labelme_json(yolo_path, image_path, output_json, class_names)

        if success:
            self._emit_log('success', f"Converted {base_name}.txt → {base_name}.json")
            self._emit_progress(1, 1)
            self._emit_finished({'total': 1, 'success': 1, 'failed': 0, 'skipped': 0, 'errors': []})
        else:
            self._emit_log('error', f"Failed to convert {base_name}.txt")
            self._emit_finished({'total': 1, 'success': 0, 'failed': 1, 'skipped': 0,
                                 'errors': [f"Failed: {base_name}.txt"]})

    def _run_batch(self, input_folder, image_folder, output_dir, class_names, extensions, conflict):
        if self._canceled:
            return

        result = batch_convert_yolo_to_labelme(
            input_folder, image_folder, output_dir, class_names,
            image_extensions=extensions,
            progress_callback=self._emit_progress,
            log_callback=self._emit_log
        )
        if not self._canceled:
            self._emit_finished(result)
