# -*- coding: utf-8 -*-
"""GUI-level regressions: construction, live language switch, conversion finish."""
import os

import pytest

import lang


def _open_tools(app):
    app._open_cropper()
    app._open_annotator()
    app.root.update()
    return app._crop_win, app._annot_win


def test_windows_construct_and_shutdown(tk_app):
    crop, annot = _open_tools(tk_app)
    assert crop is not None and annot is not None
    assert "YoloToJson" in crop.title()
    assert "YoloToJson" in annot.title()


def test_finish_conversion_succeeds_in_chinese(tk_app):
    """v1.3.3 raised KeyError('total') here, skipping the rest of the cleanup."""
    app = tk_app
    lang.set_language("zh")
    app._apply_language()
    app._last_error = None
    app._last_result = {"total": 2, "success": 2, "failed": 0, "skipped": 0,
                        "canceled": False, "errors": []}

    before = os.stat(app._settings._path).st_mtime_ns
    app._finish_conversion()                 # must not raise
    after = os.stat(app._settings._path).st_mtime_ns

    assert app._worker is None
    assert after != before, "_save_settings() was skipped"
    assert "共 2" in app._log_panel._text.get("1.0", "end")


def test_finish_conversion_reports_canceled(tk_app):
    app = tk_app
    app._last_error = None
    app._last_result = {"total": 5, "success": 2, "failed": 0, "skipped": 0,
                        "canceled": True, "errors": []}
    app._finish_conversion()                 # must not raise
    assert app._worker is None


def test_language_switch_retranslates_tool_windows(tk_app):
    app = tk_app
    lang.set_language("zh")
    app._apply_language()
    crop, annot = _open_tools(app)

    # filter state deliberately non-default: it must survive the switch
    annot._filter_state_key = "annotated"
    annot._cmb_filter_state.current(1)

    app._switch_language("en")
    app.root.update()

    assert annot._btn_save["text"] == "Save (Ctrl+S)"
    assert annot._box_panel["text"] == "Box List"
    assert annot._img_panel["text"].startswith("Image List")
    assert annot._tree.heading("cls")["text"] == "Class Name"
    assert list(crop._cmb_conflict["values"]) == ["Overwrite", "Skip"]
    # internal filter key kept, combo re-pointed at the right label
    assert annot._filter_state_key == "annotated"
    assert annot._cmb_filter_state.current() == 1

    app._switch_language("zh")
    app.root.update()
    assert annot._btn_save["text"] == "保存 (Ctrl+S)"
    assert annot._box_panel["text"] == "标注列表"


def test_language_switch_with_closed_tool_window_is_safe(tk_app):
    app = tk_app
    crop, annot = _open_tools(app)
    crop.destroy()
    app.root.update()
    app._switch_language("en")               # stale reference must not raise
    app.root.update()
    assert annot._btn_save["text"] == "Save (Ctrl+S)"


def test_annotator_image_panel_title_tracks_counts(tk_app, tmp_path):
    app = tk_app
    crop, annot = _open_tools(app)
    annot._viewer.set_files([])
    annot._refresh_img_list()
    assert "0/0" in annot._img_panel["text"]


@pytest.mark.parametrize("code,expected", [("zh", "标注列表"), ("en", "Box List")])
def test_panel_titles_follow_language(tk_app, code, expected):
    app = tk_app
    crop, annot = _open_tools(app)
    app._switch_language(code)
    app.root.update()
    assert annot._box_panel["text"] == expected
