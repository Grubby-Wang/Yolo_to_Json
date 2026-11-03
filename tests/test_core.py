# -*- coding: utf-8 -*-
"""Core conversion / annotation / cropping logic (no GUI needed)."""
import json
import os

import pytest

import image_cropper
import yolo_annotation
import yolo_to_json
from image_cropper import Region
from PIL import Image


# ── fixture helpers ──

@pytest.fixture
def dataset(tmp_path):
    """One 640x480 image + a two-box YOLO label file."""
    img_dir = tmp_path / "images"
    txt_dir = tmp_path / "labels"
    out_dir = tmp_path / "out"
    for d in (img_dir, txt_dir, out_dir):
        d.mkdir()
    Image.new("RGB", (640, 480), (0, 0, 0)).save(img_dir / "img001.JPG", "JPEG")
    (txt_dir / "img001.txt").write_text(
        "0 0.5 0.5 0.3 0.4\n1 0.2 0.3 0.1 0.15\n", encoding="utf-8")
    return {"img": img_dir, "txt": txt_dir, "out": out_dir}


# ── YOLO txt parsing / writing ──

def test_parse_returns_normalized_boxes(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("0 0.5 0.5 0.3 0.4\n", encoding="utf-8")
    boxes = yolo_annotation.parse_yolo_txt(str(path))
    assert len(boxes) == 1
    box = boxes[0]
    assert box.label == "0"
    assert box.x == pytest.approx(0.35)
    assert box.y == pytest.approx(0.3)
    assert box.w == pytest.approx(0.3)
    assert box.h == pytest.approx(0.4)


def test_parse_clamps_out_of_range_boxes(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("1 0.9 0.9 0.4 0.4\n", encoding="utf-8")
    box = yolo_annotation.parse_yolo_txt(str(path))[0]
    assert box.x + box.w <= 1.0 + 1e-9
    assert box.y + box.h <= 1.0 + 1e-9


def test_parse_skips_malformed_lines(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("0 0.5 0.5 0.3 0.4\n2\nabc 0.1 0.1 0.1 0.1\n", encoding="utf-8")
    assert len(yolo_annotation.parse_yolo_txt(str(path))) == 1


def test_parse_missing_file_is_empty(tmp_path):
    assert yolo_annotation.parse_yolo_txt(str(tmp_path / "nope.txt")) == []


def test_write_then_parse_roundtrip(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("0 0.5 0.5 0.3 0.4\n1 0.2 0.3 0.1 0.15\n", encoding="utf-8")
    boxes = yolo_annotation.parse_yolo_txt(str(src))
    dst = tmp_path / "dst.txt"
    assert yolo_annotation.write_yolo_txt(str(dst), boxes)
    again = yolo_annotation.parse_yolo_txt(str(dst))
    assert [(b.label, round(b.x, 6), round(b.y, 6), round(b.w, 6), round(b.h, 6))
            for b in boxes] == \
           [(b.label, round(b.x, 6), round(b.y, 6), round(b.w, 6), round(b.h, 6))
            for b in again]


def test_write_uses_six_decimals(tmp_path):
    dst = tmp_path / "d.txt"
    yolo_annotation.write_yolo_txt(dst.as_posix(), [Region(0.1, 0.2, 0.3, 0.4, "2")])
    text = dst.read_text(encoding="utf-8").strip()
    assert text == "2 0.250000 0.400000 0.300000 0.400000"


def test_label_path_for_swaps_extension():
    got = yolo_annotation.label_path_for(r"C:\data\a.PNG")
    assert got == r"C:\data\a.txt"


def test_classes_txt_roundtrip(tmp_path):
    path = tmp_path / "classes.txt"
    yolo_annotation.save_classes_txt(str(path), ["缺陷", "裂纹"])
    assert yolo_annotation.load_classes_txt(str(path)) == ["缺陷", "裂纹"]


def test_classes_txt_reads_gbk(tmp_path):
    path = tmp_path / "classes.txt"
    path.write_bytes("缺陷\n裂纹\n".encode("gbk"))
    assert yolo_annotation.load_classes_txt(str(path)) == ["缺陷", "裂纹"]


# ── Region coordinate math ──

def test_region_pixel_roundtrip():
    r = Region.from_pixels(64, 48, 320, 240, 640, 480)
    assert r.to_pixels(640, 480) == (64, 48, 320, 240)


def test_region_clamps_to_image_bounds():
    r = Region(0.5, 0.5, 2.0, 2.0)
    px, py, pw, ph = r.to_pixels(100, 100)
    assert px + pw <= 100 and py + ph <= 100
    assert pw >= 1 and ph >= 1


def test_region_is_meaningful_rejects_clicks():
    assert not Region.from_pixels(10, 10, 1, 1, 640, 480).is_meaningful(640, 480)
    assert Region.from_pixels(10, 10, 50, 50, 640, 480).is_meaningful(640, 480)


# ── Conversion pipeline ──

def test_batch_conversion_produces_labelme_json(dataset):
    result = yolo_to_json.batch_convert_yolo_to_labelme(
        str(dataset["txt"]), str(dataset["img"]), str(dataset["out"]),
        ["defect", "crack"])
    assert result["total"] == 1 and result["success"] == 1
    data = json.loads((dataset["out"] / "img001.json").read_text(encoding="utf-8"))
    assert data["imageWidth"] == 640 and data["imageHeight"] == 480
    assert [s["label"] for s in data["shapes"]] == ["defect", "crack"]
    assert data["shapes"][0]["points"] == [[224.0, 144.0], [416.0, 144.0],
                                          [416.0, 336.0], [224.0, 336.0]]


def test_batch_conversion_matches_case_insensitive_extension(dataset):
    # label file says img001.txt, the image is img001.JPG
    result = yolo_to_json.batch_convert_yolo_to_labelme(
        str(dataset["txt"]), str(dataset["img"]), str(dataset["out"]),
        ["defect", "crack"])
    assert result["success"] == 1


def test_batch_skip_existing_respects_conflict_action(dataset):
    args = (str(dataset["txt"]), str(dataset["img"]), str(dataset["out"]),
            ["defect", "crack"])
    assert yolo_to_json.batch_convert_yolo_to_labelme(*args)["success"] == 1
    again = yolo_to_json.batch_convert_yolo_to_labelme(
        *args, conflict_action="skip")
    assert again["skipped"] == 1 and again["success"] == 0


def test_batch_cancel_stops_early(dataset):
    result = yolo_to_json.batch_convert_yolo_to_labelme(
        str(dataset["txt"]), str(dataset["img"]), str(dataset["out"]),
        ["defect", "crack"], cancel_check=lambda: True)
    assert result["canceled"] is True and result["success"] == 0


# ── Cropping ──

def test_crop_writes_expected_size(dataset, tmp_path):
    dest = tmp_path / "cr.jpg"
    status = image_cropper.crop_image(
        str(dataset["img"] / "img001.JPG"), Region(0.1, 0.1, 0.5, 0.5), str(dest))
    assert status == "success"
    assert Image.open(dest).size == (320, 240)


def test_crop_respects_skip_conflict(dataset, tmp_path):
    dest = tmp_path / "cr.jpg"
    dest.write_bytes(b"x")
    status = image_cropper.crop_image(
        str(dataset["img"] / "img001.JPG"), Region(0.1, 0.1, 0.5, 0.5),
        str(dest), overwrite=False)
    assert status == "exists"


def test_batch_crop_counts(dataset):
    files = [str(dataset["img"] / "img001.JPG")]
    result = image_cropper.batch_crop(files, Region(0.1, 0.1, 0.5, 0.5))
    assert result == {"total": 1, "success": 1, "failed": 0, "skipped": 0,
                      "canceled": False, "errors": []}


def test_make_crop_path_suffix():
    assert image_cropper.make_crop_path(r"C:\img\a.png") == r"C:\img\a_cr.png"
    assert image_cropper.make_crop_path(r"C:\img\a.png", output_dir=r"D:\out") \
        == r"D:\out\a_cr.png"


def test_load_image_paths_sorted_and_filtered(tmp_path):
    for name in ("b.JPG", "a.png", "note.txt"):
        (tmp_path / name).write_bytes(b"")
    got = image_cropper.load_image_paths(str(tmp_path))
    assert [os.path.basename(p) for p in got] == ["a.png", "b.JPG"]
