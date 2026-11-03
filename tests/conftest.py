# -*- coding: utf-8 -*-
"""Shared fixtures: isolate config.ini and keep the GUI tests off-screen."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def _isolate_language():
    """Start every test in Chinese with no listeners left by a previous window."""
    import lang
    lang._listeners.clear()
    lang.set_language("zh")
    yield
    lang._listeners.clear()
    lang.set_language("zh")


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    """Point SettingsManager at a throwaway directory instead of the repo."""
    import settings_manager
    monkeypatch.setattr(settings_manager, "_app_dir", lambda: str(tmp_path))
    return tmp_path


@pytest.fixture
def settings(app_dir):
    import settings_manager
    return settings_manager.SettingsManager()


@pytest.fixture
def tk_app(settings, tmp_path, monkeypatch):
    """A fully constructed, withdrawn main window plus its settings."""
    import tkinter as tk
    try:
        probe = tk.Tk()
    except tk.TclError as exc:            # no display available
        pytest.skip(f"tkinter unavailable: {exc}")
    else:
        probe.destroy()

    import main
    app = main.YoloToJsonApp()
    app.root.withdraw()
    app.root.update()
    yield app
    try:
        if app.root.winfo_exists():
            app.root.destroy()
    except Exception:
        pass
