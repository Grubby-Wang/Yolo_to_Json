"""
Background worker for conversion operations (runs in a thread).
Uses stdlib threading — no Qt dependency.
Calls back to the GUI via a queue polled by tkinter's .after().
"""

import os
import threading

import lang
from yolo_to_json import (
    DEFAULT_IMAGE_EXTENSIONS,
    batch_convert_yolo_to_labelme,
    find_image_file,
    yolo_to_labelme_json,
)


class ConversionWorker:
    """Runs YOLO→JSON conversion in a background thread.

    The cancel flag is checked between files inside the batch loop, so
    cancel() stops the run promptly; the partial result (with
    result['canceled'] = True) is still reported via on_finished.
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
        if self.on_progress:
            self.on_progress(current, total)

    def _emit_log(self, level, message):
        if self.on_log:
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
        extensions = self._config.get('extensions', DEFAULT_IMAGE_EXTENSIONS)
        conflict = self._config.get('conflict_action', 'overwrite')

        if self._canceled:
            return

        if not input_path:
            self._emit_error(lang.tr('no_input_path'))
            return

        if not output_dir:
            self._emit_error(lang.tr('no_output_path'))
            return

        try:
            if mode == 'single':
                self._run_single(input_path, image_folder, output_dir, class_names, conflict)
            else:
                self._run_batch(input_path, image_folder, output_dir,
                                class_names, extensions, conflict)
        except Exception as e:
            self._emit_error(str(e))

    def _run_single(self, yolo_path, image_folder, output_dir, class_names, conflict):
        base_name = os.path.splitext(os.path.basename(yolo_path))[0]

        if os.path.isfile(image_folder):
            image_path = image_folder
        else:
            extensions = self._config.get('extensions', DEFAULT_IMAGE_EXTENSIONS)
            image_path = find_image_file(image_folder, base_name, extensions)

        if image_path is None:
            self._emit_error(lang.tr('no_match_image', base=base_name))
            return

        output_json = os.path.join(output_dir, base_name + ".json")

        if os.path.exists(output_json) and conflict == 'skip':
            self._emit_log('warn', lang.tr('log_skip_exists', base=base_name))
            self._emit_finished({'total': 1, 'success': 0, 'failed': 0, 'skipped': 1,
                                 'canceled': False, 'errors': []})
            return

        os.makedirs(output_dir, exist_ok=True)
        success = yolo_to_labelme_json(yolo_path, image_path, output_json, class_names)

        if success:
            self._emit_log('success', lang.tr('log_converted', base=base_name))
            self._emit_progress(1, 1)
            self._emit_finished({'total': 1, 'success': 1, 'failed': 0, 'skipped': 0,
                                 'canceled': False, 'errors': []})
        else:
            self._emit_log('error', lang.tr('log_failed', base=base_name))
            self._emit_finished({'total': 1, 'success': 0, 'failed': 1, 'skipped': 0,
                                 'canceled': False,
                                 'errors': [lang.tr('log_failed', base=base_name)]})

    def _run_batch(self, input_folder, image_folder, output_dir,
                   class_names, extensions, conflict):
        status_level = {'success': 'success', 'failed': 'error',
                        'no_image': 'warn', 'exists': 'warn'}
        status_key = {'success': 'log_converted', 'failed': 'log_failed',
                      'no_image': 'log_skipped', 'exists': 'log_skip_exists'}

        def on_file(base_name, status):
            self._emit_log(status_level[status],
                           lang.tr(status_key[status], base=base_name))

        result = batch_convert_yolo_to_labelme(
            input_folder, image_folder, output_dir, class_names,
            image_extensions=extensions,
            conflict_action=conflict,
            cancel_check=lambda: self._canceled,
            file_callback=on_file,
            progress_callback=self._emit_progress,
            log_callback=self._emit_log,
        )
        self._emit_finished(result)
