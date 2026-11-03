# -*- coding: utf-8 -*-
"""i18n consistency: every key translated, every placeholder satisfiable."""
import ast
import os
import re

import pytest

import lang

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def _source_files():
    for name in os.listdir(ROOT):
        if name.endswith(".py"):
            yield name, os.path.join(ROOT, name)


def _tr_call_keys():
    """Every literal key passed to lang.tr(...) anywhere in the app."""
    used = {}
    for name, path in _source_files():
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=name)
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "tr"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                key = node.args[0].value
                kwargs = {kw.arg for kw in node.keywords if kw.arg}
                used.setdefault(key, set()).update(kwargs)
    return used


def test_every_entry_has_both_languages():
    missing = [k for k, v in lang.STRINGS.items()
               if "zh" not in v or "en" not in v]
    assert missing == []


def test_no_empty_translations():
    empty = [k for k, v in lang.STRINGS.items()
             if not v["zh"].strip() or not v["en"].strip()]
    assert empty == []


def test_placeholders_match_across_languages():
    """zh and en must expose the same names, or one language silently loses data."""
    mismatched = {}
    for key, entry in lang.STRINGS.items():
        zh = set(PLACEHOLDER.findall(entry["zh"]))
        en = set(PLACEHOLDER.findall(entry["en"]))
        if zh != en:
            mismatched[key] = (sorted(zh), sorted(en))
    assert mismatched == {}


def test_every_used_key_is_defined():
    undefined = sorted(k for k in _tr_call_keys() if k not in lang.STRINGS)
    assert undefined == []


def test_every_call_site_passes_required_placeholders():
    """Regression for the v1.3.3 KeyError: tr('log_complete') without total."""
    problems = []
    for key, kwargs in _tr_call_keys().items():
        if key not in lang.STRINGS:
            continue
        for code in ("zh", "en"):
            need = set(PLACEHOLDER.findall(lang.STRINGS[key][code]))
            missing = need - kwargs
            if kwargs and missing:
                problems.append(f"{key}[{code}] needs {sorted(missing)}")
    assert problems == []


def test_tr_does_not_raise_on_missing_key(recwarn):
    assert lang.tr("definitely_not_a_key") == "definitely_not_a_key"
    assert any("undefined key" in str(w.message) for w in recwarn)


def test_tr_does_not_raise_on_placeholder_mismatch(recwarn):
    lang.set_language("zh")
    out = lang.tr("log_complete", success=1, failed=0, skipped=0)
    assert "{total}" in out              # raw template, not a traceback
    assert any("placeholder mismatch" in str(w.message) for w in recwarn)


def test_tr_formats_when_complete():
    lang.set_language("zh")
    assert lang.tr("log_complete", success=1, failed=2, skipped=3, total=6) == \
        "转换完成。成功 1，失败 2，跳过 3（共 6）。"


@pytest.mark.parametrize("code", ["zh", "en"])
def test_log_complete_keeps_total_in_both_languages(code):
    lang.set_language(code)
    assert "6" in lang.tr("log_complete", success=1, failed=2, skipped=3, total=6)
