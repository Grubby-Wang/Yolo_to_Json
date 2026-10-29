"""
Image Cropping — Core Logic (no GUI)

A crop region is stored in normalized coordinates (0~1 relative to image
width/height) so the same region can be applied across images of different
sizes. The optional `label` field is reserved for the future YOLO
annotation module built on the same viewer base.
"""

import os
from dataclasses import dataclass, field

from PIL import Image

import lang


CROP_SUFFIX = "_cr"

# file status → (log level, lang key)
_CROP_STATUS_LOG = {
    'success': ('success', 'crop_done'),
    'failed':  ('error',   'crop_failed'),
    'exists':  ('warn',    'crop_skip_exists'),
}


@dataclass
class Region:
    """Normalized rectangle: x, y, w, h are fractions of image width/height."""
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    label: str = ""  # reserved for YOLO annotation

    def to_pixels(self, width, height):
        """Pixel box (px, py, pw, ph) clamped to image bounds, min 1x1."""
        px = max(0, min(round(self.x * width), width - 1))
        py = max(0, min(round(self.y * height), height - 1))
        pw = max(1, min(round(self.w * width), width - px))
        ph = max(1, min(round(self.h * height), height - py))
        return px, py, pw, ph

    @classmethod
    def from_pixels(cls, px, py, pw, ph, width, height, label=""):
        px = max(0, min(px, width - 1))
        py = max(0, min(py, height - 1))
        pw = max(1, min(pw, width - px))
        ph = max(1, min(ph, height - py))
        return cls(px / width, py / height, pw / width, ph / height, label)

    def is_meaningful(self, width, height, min_px=3):
        """False for accidental clicks (rect smaller than min_px in image px)."""
        pw = self.w * width
        ph = self.h * height
        return pw >= min_px and ph >= min_px


def make_crop_path(src_path, suffix=CROP_SUFFIX, output_dir=None):
    """img001.jpg → img001_cr.jpg (same folder, or output_dir if given)."""
    folder, name = os.path.split(src_path)
    stem, ext = os.path.splitext(name)
    dest = os.path.join(output_dir if output_dir else folder, stem + suffix + ext)
    return dest


def crop_image(src_path, region, dest_path, overwrite=True):
    """Crop one image by a normalized Region and save to dest_path.

    Returns 'success', 'exists' (dest exists and overwrite=False), or 'failed'.
    """
    if not overwrite and os.path.exists(dest_path):
        return 'exists'
    try:
        with Image.open(src_path) as img:
            width, height = img.size
            px, py, pw, ph = region.to_pixels(width, height)
            cropped = img.crop((px, py, px + pw, py + ph))
            # JPEG can't store palette or alpha channels
            if dest_path.lower().endswith(('.jpg', '.jpeg')) and \
                    cropped.mode not in ('RGB', 'L', 'CMYK'):
                cropped = cropped.convert('RGB')
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            cropped.save(dest_path)
        return 'success'
    except Exception:
        return 'failed'


def batch_crop(image_paths, region, output_dir=None, conflict='overwrite',
               cancel_check=None, file_callback=None,
               progress_callback=None, log_callback=None):
    """Apply one normalized Region to many images (crop + save each).

    Output naming follows make_crop_path(); output_dir overrides the
    per-image folder when provided.

    Returns dict: total, success, failed, skipped, canceled, errors (list).
    """
    result = {'total': len(image_paths), 'success': 0, 'failed': 0,
              'skipped': 0, 'canceled': False, 'errors': []}

    if not image_paths:
        return result

    if log_callback:
        log_callback('info', lang.tr('crop_batch_start',
                                     n=result['total'],
                                     path=output_dir if output_dir else
                                     lang.tr('crop_dir_source')))

    for idx, src in enumerate(image_paths):
        if cancel_check and cancel_check():
            result['canceled'] = True
            break

        dest = make_crop_path(src, output_dir=output_dir)
        status = crop_image(src, region, dest, overwrite=(conflict == 'overwrite'))

        if file_callback:
            file_callback(os.path.basename(src), status)
        else:
            level, key = _CROP_STATUS_LOG[status]
            if log_callback:
                log_callback(level, lang.tr(key, base=os.path.basename(src)))
            elif status == 'failed':
                result['errors'].append(lang.tr('crop_failed',
                                                base=os.path.basename(src)))

        if status == 'success':
            result['success'] += 1
        elif status == 'exists':
            result['skipped'] += 1
        else:
            result['failed'] += 1

        if progress_callback:
            progress_callback(idx + 1, result['total'])

    return result


def load_image_paths(folder, extensions=None):
    """All image files in folder (case-insensitive extensions), sorted."""
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    allowed = {ext.lower() for ext in extensions}
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    paths = [os.path.join(folder, n) for n in names
             if os.path.splitext(n)[1].lower() in allowed]
    return sorted(paths)
