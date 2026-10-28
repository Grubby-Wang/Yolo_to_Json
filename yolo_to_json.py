"""
YOLO to LabelMe JSON Converter — Core Logic

YOLO format: class_id x_center y_center box_width box_height (normalized)
Output: LabelMe JSON with rectangle shapes
"""

import os
import json
from PIL import Image

import lang


# Single source of truth for supported image extensions (GUI and worker use this too)
DEFAULT_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

# file status → (log level, lang key), used when a log_callback is given
_FILE_STATUS_LOG = {
    'success':  ('success', 'log_converted'),
    'failed':   ('error',   'log_failed'),
    'no_image': ('warn',    'log_skipped'),
    'exists':   ('warn',    'log_skip_exists'),
}


def yolo_to_labelme_json(yolo_file_path, image_path, output_json_path, class_names):
    """Convert a single YOLO .txt file to LabelMe JSON.

    Args:
        yolo_file_path: Path to YOLO format .txt file.
        image_path: Path to corresponding image file.
        output_json_path: Destination path for JSON output.
        class_names: List of class label strings (index = class_id).

    Returns:
        True on success, False on failure.
    """
    if not os.path.exists(image_path):
        return False

    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception:
        return False

    try:
        with open(yolo_file_path, 'r') as f:
            lines = f.readlines()
    except Exception:
        return False

    shapes = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 5:
            continue

        try:
            class_id, x_center, y_center, box_width, box_height = map(float, parts[:5])
        except ValueError:
            continue

        class_id = int(class_id)
        label = class_names[class_id] if class_id < len(class_names) else f"class_{class_id}"

        x = (x_center * width) - (box_width * width / 2)
        y = (y_center * height) - (box_height * height / 2)
        w = box_width * width
        h = box_height * height

        x = max(0, min(x, width))
        y = max(0, min(y, height))
        w = min(w, width - x)
        h = min(h, height - y)

        shapes.append({
            "label": label,
            "points": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        })

    labelme_data = {
        "version": "4.5.6",
        "flags": {},
        "shapes": shapes,
        "lineColor": [0, 255, 0, 128],
        "fillColor": [255, 0, 0, 128],
        "imagePath": os.path.basename(image_path),
        "imageData": None,
        "imageHeight": height,
        "imageWidth": width
    }

    out_dir = os.path.dirname(output_json_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(labelme_data, f, indent=2)

    return True


def find_image_file(image_folder, base_name, image_extensions=None):
    """Case-insensitive lookup of `<base_name><ext>` inside image_folder."""
    if image_extensions is None:
        image_extensions = DEFAULT_IMAGE_EXTENSIONS
    if not os.path.isdir(image_folder):
        return None
    allowed = {ext.lower() for ext in image_extensions}
    base_lower = base_name.lower()
    for fname in os.listdir(image_folder):
        stem, ext = os.path.splitext(fname)
        if ext.lower() in allowed and stem.lower() == base_lower:
            return os.path.join(image_folder, fname)
    return None


def list_yolo_txt_files(input_folder):
    """All .txt files in input_folder (case-insensitive), sorted by name."""
    return sorted(f for f in os.listdir(input_folder) if f.lower().endswith('.txt'))


def batch_convert_yolo_to_labelme(
    input_folder, image_folder, output_folder, class_names,
    image_extensions=None, conflict_action='overwrite',
    cancel_check=None, file_callback=None,
    progress_callback=None, log_callback=None
):
    """Batch convert YOLO .txt files to LabelMe JSON.

    Args:
        input_folder: Directory containing YOLO .txt files.
        image_folder: Directory containing corresponding images.
        output_folder: Destination directory for JSON files.
        class_names: List of class label strings (index = class_id).
        image_extensions: List of supported image extensions.
        conflict_action: 'overwrite' or 'skip' when the output JSON already exists.
        cancel_check: Optional callable() returning True to abort the loop
            between files (already-processed files are kept).
        file_callback: Optional callable(base_name, status) with status in
            {'success', 'failed', 'no_image', 'exists'}.
        progress_callback: Optional callable(current, total) for progress.
        log_callback: Optional callable(level, message) for folder-level logging.

    Returns:
        dict with keys: total, success, failed, skipped, canceled, errors (list).
    """
    if image_extensions is None:
        image_extensions = DEFAULT_IMAGE_EXTENSIONS

    result = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0,
              'canceled': False, 'errors': []}

    input_folder = os.path.normpath(input_folder)
    image_folder = os.path.normpath(image_folder)
    output_folder = os.path.normpath(output_folder)

    if not os.path.isdir(input_folder):
        msg = lang.tr('log_input_missing', path=input_folder)
        if log_callback:
            log_callback('error', msg)
        result['errors'].append(msg)
        return result

    yolo_files = list_yolo_txt_files(input_folder)
    total = len(yolo_files)
    result['total'] = total
    if not total:
        msg = lang.tr('log_no_txt', path=input_folder)
        if log_callback:
            log_callback('warn', msg)
        result['errors'].append(msg)
        return result

    # Build a case-insensitive index of the image folder once (also avoids
    # one filesystem stat per extension per txt file).
    allowed_exts = {ext.lower() for ext in image_extensions}
    image_index = {}
    if os.path.isdir(image_folder):
        for fname in os.listdir(image_folder):
            stem, ext = os.path.splitext(fname)
            if ext.lower() in allowed_exts:
                image_index.setdefault((stem + ext).lower(),
                                       os.path.join(image_folder, fname))

    os.makedirs(output_folder, exist_ok=True)
    if log_callback:
        log_callback('info', lang.tr('log_found_files', n=total))

    def report_file(base_name, status):
        if file_callback:
            file_callback(base_name, status)
        elif log_callback:
            level, key = _FILE_STATUS_LOG[status]
            log_callback(level, lang.tr(key, base=base_name))
        else:
            _, key = _FILE_STATUS_LOG[status]
            result['errors'].append(lang.tr(key, base=base_name))

    for idx, fname in enumerate(yolo_files):
        if cancel_check and cancel_check():
            result['canceled'] = True
            break

        base_name = os.path.splitext(fname)[0]

        image_path = None
        for ext in image_extensions:
            image_path = image_index.get((base_name + ext).lower())
            if image_path:
                break

        if image_path is None:
            result['skipped'] += 1
            report_file(base_name, 'no_image')
            if progress_callback:
                progress_callback(idx + 1, total)
            continue

        output_json_path = os.path.join(output_folder, base_name + ".json")

        if conflict_action == 'skip' and os.path.exists(output_json_path):
            result['skipped'] += 1
            report_file(base_name, 'exists')
        elif yolo_to_labelme_json(os.path.join(input_folder, fname),
                                  image_path, output_json_path, class_names):
            result['success'] += 1
            report_file(base_name, 'success')
        else:
            result['failed'] += 1
            report_file(base_name, 'failed')

        if progress_callback:
            progress_callback(idx + 1, total)

    return result
