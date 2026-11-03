# -*- coding: utf-8 -*-
"""config.ini persistence: legacy encodings must never block startup."""
import configparser
import os

import pytest

import settings_manager


def _write(path, text, encoding):
    with open(path, "w", encoding=encoding) as f:
        f.write(text)


LEGACY_GBK = (
    "[Settings]\n"
    "conflict_action = 覆盖\n"
    'class_names = {"0": "缺陷"}\n'
    "last_input_dir = I:/图像/测试\n"
)


def test_missing_file_uses_defaults(app_dir):
    sm = settings_manager.SettingsManager()
    assert sm.conflict_action == "overwrite"
    assert sm.class_names == {"0": "defect"}
    assert sm.language == "zh"


def test_utf8_roundtrip(app_dir, settings):
    settings.class_names = {"0": "缺陷", "1": "裂纹"}
    settings.last_input_dir = "I:/图像/测试"
    reloaded = settings_manager.SettingsManager()
    assert reloaded.class_names == {"0": "缺陷", "1": "裂纹"}
    assert reloaded.last_input_dir == "I:/图像/测试"


def test_gbk_config_is_migrated_not_fatal(app_dir):
    """A config.ini written by an older GBK build used to crash startup."""
    path = os.path.join(str(app_dir), "config.ini")
    _write(path, LEGACY_GBK, "gbk")

    sm = settings_manager.SettingsManager()          # must not raise
    assert sm.legacy_encoding == "gbk"
    assert sm.legacy_backup and os.path.exists(sm.legacy_backup)
    assert sm.conflict_action == "overwrite"         # '覆盖' normalized
    assert sm.class_names == {"0": "缺陷"}           # decoded correctly, not mojibake

    # migrated in place: the file is now UTF-8 and re-reads cleanly
    with open(path, "rb") as f:
        raw = f.read()
    assert raw.decode("utf-8")
    again = settings_manager.SettingsManager()
    assert again.legacy_encoding is None
    assert again.class_names == {"0": "缺陷"}


def test_utf8_bom_config(app_dir):
    path = os.path.join(str(app_dir), "config.ini")
    _write(path, "[Settings]\nconflict_action = skip\n", "utf-8-sig")
    sm = settings_manager.SettingsManager()
    assert sm.conflict_action == "skip"


def test_structurally_broken_config_falls_back(app_dir):
    path = os.path.join(str(app_dir), "config.ini")
    _write(path, "this is not an ini file\n横竖不是\n", "utf-8")
    sm = settings_manager.SettingsManager()          # must not raise
    assert sm.conflict_action == "overwrite"
    assert sm.legacy_backup and os.path.exists(sm.legacy_backup)


def test_undecodable_bytes_never_raise(app_dir):
    path = os.path.join(str(app_dir), "config.ini")
    with open(path, "wb") as f:
        f.write(b"[Settings]\nlast_input_dir = \xff\xfe\x00bad\n")
    sm = settings_manager.SettingsManager()          # must not raise
    assert isinstance(sm.last_input_dir, str)


@pytest.mark.parametrize("stored,expected", [
    ("overwrite", "overwrite"),
    ("skip", "skip"),
    ("SKIP", "skip"),
    ("跳过", "skip"),
    ("覆盖", "overwrite"),
    ("garbage", "overwrite"),
])
def test_conflict_action_normalization(app_dir, stored, expected):
    path = os.path.join(str(app_dir), "config.ini")
    _write(path, f"[Settings]\nconflict_action = {stored}\n", "utf-8")
    assert settings_manager.SettingsManager().conflict_action == expected


def test_annot_last_class_is_clamped_and_typed(app_dir, settings):
    settings.annot_last_class = 3
    assert settings.annot_last_class == 3
    settings.set_str("annot_last_class", "not-a-number")
    assert settings.annot_last_class == 0
    settings.set_str("annot_last_class", "-5")
    assert settings.annot_last_class == 0
