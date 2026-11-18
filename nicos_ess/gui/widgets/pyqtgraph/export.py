"""Save and print pyqtgraph plots."""

import re
import tempfile
import time
from pathlib import Path

import pyqtgraph.exporters
from pyqtgraph.Qt import QtSvg

from nicos.guisupport.qt import (
    QDialog,
    QFileDialog,
    QPainter,
    QPrintDialog,
    QPrinter,
    Qt,
)

IMAGE_FILTERS = {
    ".png": "PNG image (*.png)",
    ".pdf": "PDF document (*.pdf)",
    ".svg": "SVG image (*.svg)",
}
QUIET_FORMATS = (".svg", ".png")


def export_plot(plot_widget, path):
    """Export what the graphics view *plot_widget* shows to *path*.

    The suffix of *path* chooses the format, which is .png, .svg or .pdf.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".png":
        pyqtgraph.exporters.ImageExporter(plot_widget.scene()).export(str(path))
    elif suffix == ".svg":
        generator = QtSvg.QSvgGenerator()
        generator.setFileName(str(path))
        generator.setSize(plot_widget.size())
        generator.setViewBox(plot_widget.rect())
        _render(plot_widget, generator)
    elif suffix == ".pdf":
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(path))
        _render(plot_widget, printer)
    else:
        raise ValueError(f"unsupported plot format: {suffix or path.name}")
    return str(path)


# This is the file that any plot saved last. The next file goes to the same folder.
_saved = "plot"


def save_plot_dialog(plot_widget, parent=None):
    """Ask for a file name and export the plot to it.

    The default name is <plot>_<time> in the folder of the last saved plot.
    """
    global _saved
    name = getattr(getattr(plot_widget, "view", None), "name", "plot")
    name = re.sub(r"[^\w.-]+", "_", name)
    default = Path(_saved).with_name(f"{name}_{time.strftime('%Y-%m-%d_%H%M%S')}")
    path, selected = QFileDialog.getSaveFileName(
        parent,
        "Save plot as...",
        str(default),
        ";;".join(IMAGE_FILTERS.values()),
        IMAGE_FILTERS[".png"],
    )
    if path and Path(path).suffix.lower() not in IMAGE_FILTERS:
        path += next(k for k, v in IMAGE_FILTERS.items() if v == selected)
    if path:
        _saved = export_plot(plot_widget, path)
    return path and _saved


def save_plot_quietly(plot_widget):
    """Export the plot to temporary files and return (path, suffix) pairs."""
    saved = []
    for suffix in QUIET_FORMATS:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            pass
        saved.append((export_plot(plot_widget, handle.name), suffix))
    return saved


def print_plot(plot_widget, parent=None):
    """Print the plot after a print dialog and return whether it was printed."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    if QPrintDialog(printer, parent).exec() != QDialog.DialogCode.Accepted:
        return False
    _render(plot_widget, printer)
    return True


def _render(plot_widget, device):
    painter = QPainter(device)
    page, size = painter.viewport(), plot_widget.size()
    size.scale(page.size(), Qt.AspectRatioMode.KeepAspectRatio)
    painter.setViewport(page.x(), page.y(), size.width(), size.height())
    painter.setWindow(plot_widget.rect())
    plot_widget.render(painter)
    painter.end()
