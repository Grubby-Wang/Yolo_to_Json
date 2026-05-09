"""
YOLO to LabelMe JSON Converter — Core Logic

YOLO format: class_id x_center y_center box_width box_height (normalized)
Output: LabelMe JSON with rectangle shapes
"""

import os
import json
import re
from PIL import Image


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

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(labelme_data, f, indent=2)

    return True


def batch_convert_yolo_to_labelme(
    input_folder, image_folder, output_folder, class_names,
    image_extensions=None, progress_callback=None, log_callback=None
):
    """Batch convert YOLO .txt files to LabelMe JSON.

    Args:
        input_folder: Directory containing YOLO .txt files.
        image_folder: Directory containing corresponding images.
        output_folder: Destination directory for JSON files.
        class_names: List of class label strings.
        image_extensions: List of supported image extensions.
        progress_callback: Optional callable(current, total) for progress.
        log_callback: Optional callable(level, message) for logging.

    Returns:
        dict with keys: total, success, failed, skipped, errors (list).
    """
    if image_extensions is None:
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

    input_folder = os.path.normpath(input_folder)
    image_folder = os.path.normpath(image_folder)
    output_folder = os.path.normpath(output_folder)

    os.makedirs(output_folder, exist_ok=True)

    if not os.path.exists(input_folder):
        msg = f"Input folder does not exist: {input_folder}"
        if log_callback:
            log_callback('error', msg)
        return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'errors': [msg]}

    txt_pattern = re.compile(r'\.txt$', re.IGNORECASE)
    all_files = os.listdir(input_folder)
    yolo_files = [os.path.join(input_folder, f) for f in all_files if txt_pattern.search(f)]

    if not yolo_files:
        msg = f"No .txt files found in {input_folder}"
        if log_callback:
            log_callback('warn', msg)
        return {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'errors': [msg]}

    total = len(yolo_files)
    if log_callback:
        log_callback('info', f"Found {total} YOLO file(s), starting conversion...")

    success = 0
    failed = 0
    skipped = 0
    errors = []

    for idx, yolo_file in enumerate(yolo_files):
        base_name = os.path.splitext(os.path.basename(yolo_file))[0]

        image_path = None
        for ext in image_extensions:
            for case_ext in (ext, ext.upper()):
                candidate = os.path.join(image_folder, base_name + case_ext)
                if os.path.exists(candidate):
                    image_path = candidate
                    break
            if image_path:
                break

        if image_path is None:
            skipped += 1
            msg = f"Skipped {base_name}.txt — no matching image found"
            if log_callback:
                log_callback('warn', msg)
            else:
                errors.append(msg)
            if progress_callback:
                progress_callback(idx + 1, total)
            continue

        output_json_path = os.path.join(output_folder, base_name + ".json")

        if yolo_to_labelme_json(yolo_file, image_path, output_json_path, class_names):
            success += 1
            if log_callback:
                log_callback('success', f"Converted {base_name}.txt → {base_name}.json")
        else:
            failed += 1
            msg = f"Failed to convert {base_name}.txt"
            if log_callback:
                log_callback('error', msg)
            else:
                errors.append(msg)

        if progress_callback:
            progress_callback(idx + 1, total)

    result = {
        'total': total,
        'success': success,
        'failed': failed,
        'skipped': skipped,
        'errors': errors
    }

    if log_callback:
        log_callback('info',
            f"Done. {success} success, {failed} failed, {skipped} skipped (of {total} total)")

    return result
