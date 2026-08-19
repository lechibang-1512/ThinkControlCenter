"""GTK4 / Libadwaita application entry point."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from thinkcontrolcenter.config import APP_ID
from thinkcontrolcenter.utils import get_style_css_path
from thinkcontrolcenter.window import ThinkControlCenterWindow


class ThinkControlCenterApp(Adw.Application):
    """Top-level Adw.Application that bootstraps the window and CSS theme."""

    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self) -> None:
        """Called when the application is activated (on launch or focus)."""
        style_mgr = Adw.StyleManager.get_default()
        style_mgr.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_path(get_style_css_path())
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        self._window = ThinkControlCenterWindow(self)
        self._window.present()


def main() -> int:
    """Create and run the application."""
    app = ThinkControlCenterApp()
    return app.run(sys.argv)
