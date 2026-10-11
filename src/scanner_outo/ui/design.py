"""Stitch tokens in logical pixels; no network resources at runtime."""
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).parent / "assets"
COLORS = {
    "action": "#0F766E", "deep": "#005C55", "rail": "#213145",
    "base": "#F8F9FF", "work": "#EFF4FF", "card": "#FFFFFF",
    "surface": "#E5EEFF", "selection": "#DCE9FF", "text": "#0B1C30",
    "secondary": "#3E4947", "neutral": "#64748B", "border": "#BDC9C6",
    "success": "#9CF2E8", "warning": "#9C573A", "error_bg": "#FFDAD6",
    "error_text": "#93000A", "destructive": "#BA1A1A",
}
SPACING = (4, 8, 16, 24, 32)
FONT_SIZES = {"title": 28, "section": 20, "subtitle": 16, "body": 13,
              "secondary": 12, "label": 11, "metric": 20, "technical": 11}
_loaded = False


def load_fonts():
    global _loaded
    if not _loaded:
        for path in (ASSETS / "fonts").glob("*.ttf"):
            if QFontDatabase.addApplicationFont(str(path)) < 0:
                raise RuntimeError(f"Fonte local invalida: {path.name}")
        _loaded = True


def font(size=13, mono=False, bold=False):
    result = QFont("JetBrains Mono" if mono else "Inter")
    result.setPixelSize(size)
    result.setWeight(QFont.Weight.DemiBold if bold else QFont.Weight.Normal)
    result.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0)
    return result


def icon(name, color="#0F766E"):
    path = ASSETS / "icons" / f"{name}.svg"
    if not path.is_file():
        raise RuntimeError(f"Icone local em falta: {name}")
    renderer = QSvgRenderer(QByteArray(path.read_bytes()))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    result = QIcon(pixmap)
    disabled = pixmap.copy()
    painter = QPainter(disabled)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(disabled.rect(), QColor(COLORS["secondary"]))
    painter.end()
    result.addPixmap(disabled, QIcon.Mode.Disabled)
    return result
