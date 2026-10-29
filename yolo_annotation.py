"""
YOLO Annotation — Core Logic (no GUI)

Read/write YOLO detection labels: `class_id x_center y_center width height`
per line, normalized to 0~1. Boxes are exchanged with the shared Region
dataclass (label field carries the class_id as a string).
"""

import os

import lang
from image_cropper import Region


def parse_yolo_txt(path):
    """Parse a YOLO label file into Regions.

    Returns [] when the file is missing or unreadable; malformed lines
    are skipped. Region.label holds the class_id as a string.
    """
    boxes = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        try:
            with open(path, 'r', encoding='gbk') as f:
                lines = f.readlines()
        except Exception:
            return []
    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            cid = int(float(parts[0]))
            cx, cy, w, h = (float(v) for v in parts[1:5])
        except ValueError:
            continue
        # clamp to unit square, keep at least a sliver of a box
        w = min(max(w, 0.0), 1.0)
        h = min(max(h, 0.0), 1.0)
        cx = min(max(cx, 0.0), 1.0)
        cy = min(max(cy, 0.0), 1.0)
        x0 = min(max(cx - w / 2, 0.0), 1.0)
        y0 = min(max(cy - h / 2, 0.0), 1.0)
        x1 = min(max(cx + w / 2, 0.0), 1.0)
        y1 = min(max(cy + h / 2, 0.0), 1.0)
        if x1 - x0 <= 0 or y1 - y0 <= 0:
            continue
        boxes.append(Region(x0, y0, x1 - x0, y1 - y0, str(cid)))
    return boxes


def write_yolo_txt(path, regions):
    """Write Regions as a YOLO label file (UTF-8, 6-decimal coordinates).

    Returns True on success.
    """
    lines = []
    for r in regions:
        cid = str(r.label) if str(r.label).lstrip('-').isdigit() else "0"
        cx = min(max(r.x + r.w / 2, 0.0), 1.0)
        cy = min(max(r.y + r.h / 2, 0.0), 1.0)
        w = min(max(r.w, 0.0), 1.0)
        h = min(max(r.h, 0.0), 1.0)
        lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    try:
        out_dir = os.path.dirname(path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        return True
    except OSError:
        return False


def load_classes_txt(path):
    """YOLO classes.txt: one class name per line, line number (0-based) = class ID."""
    for encoding in ('utf-8-sig', 'gbk'):
        try:
            with open(path, 'r', encoding=encoding) as f:
                return [ln.strip() for ln in f if ln.strip()]
        except UnicodeDecodeError:
            continue
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return [ln.strip() for ln in f if ln.strip()]


def save_classes_txt(path, names):
    """Write class names one per line (YOLO classes.txt format)."""
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(names) + ("\n" if names else ""))


def label_path_for(image_path):
    """a.PNG → a.txt next to the image (standard YOLO layout)."""
    folder, name = os.path.split(image_path)
    return os.path.join(folder, os.path.splitext(name)[0] + ".txt")


def region_summary(region, class_names):
    """Human-readable 'id name cx cy w h' for lists and logs."""
    try:
        cid = int(region.label)
    except (TypeError, ValueError):
        cid = -1
    name = class_names[cid] if 0 <= cid < len(class_names) else \
        lang.tr('class_default_name', n=cid)
    return cid, name, (region.x + region.w / 2), (region.y + region.h / 2), region.w, region.h
