"""
Shared UI theme constants (colors, fonts) for all YoloToJson windows.
"""

# ── Color theme ──

BG_MAIN     = "#F0F2F5"
BG_PANEL    = "#FFFFFF"
BG_INPUT    = "#FFFFFF"
BG_BUTTON   = "#F5F6F8"
FG_PRIMARY  = "#1F2937"
FG_ACCENT   = "#2563EB"
FG_SUCCESS  = "#059669"
FG_WARN     = "#D97706"
FG_ERROR    = "#DC2626"
ACCENT_BLUE = "#2563EB"
BORDER      = "#D1D5DB"

CANVAS_BG   = "#2B2D31"
CANVAS_FG   = "#9CA3AF"
RECT_COLOR  = "#FF3B30"

# Log levels → colors
LEVEL_COLORS = {
    'info':    FG_PRIMARY,
    'success': FG_SUCCESS,
    'warn':    FG_WARN,
    'error':   FG_ERROR,
}

# Annotation box palette (cycled by class id)
BOX_PALETTE = [
    "#FF3B30", "#FF9500", "#FFCC00", "#34C759", "#00C7BE",
    "#30B0C7", "#007AFF", "#5856D6", "#AF52DE", "#FF2D55",
]

# ── Fonts ──

FONT_MONO   = ("Consolas", 10)
FONT_UI     = ("Segoe UI", 10)
FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_BTN    = ("Segoe UI", 10, "bold")
