"""Non-blocking BUI file browser, sharing the desktop's existing event loop.

BUI 0.4.1's blocking filebrowser.ask() recursively pumps the native macOS
loop. Closing that dialog corrupts the outer Cocoa autorelease pool. Keep the
Blender browser, but poll its state with the parent window's normal timers.
"""
from pathlib import Path

import buipy
from blenderui import filebrowser, host


class FileDialog:
    def __init__(self, owner, kind, *, on_result, title, initialfile=None,
                 initialdir=None, defaultextension=None, filetypes=None):
        if owner is None or not owner.is_open:
            raise RuntimeError('Open the desktop window before choosing a file.')
        self.owner, self.on_result = owner, on_result
        self.kind, self.extension = kind, defaultextension
        self.finished = self.cancelled = False
        self.timer = None
        self.browser = buipy.KitNode('filebrowser')
        self.browser.set('mode', {'open': 0, 'save': 1}[kind])
        for key, value in [('file', initialfile), ('dir', initialdir),
                           ('filters', filebrowser.tk_filters(filetypes))]:
            if value:
                self.browser.set(key, value)
        self.context = buipy.KitContext(self.browser)
        self.window = host.Window(self.context, title,
            (int(self.browser.get('dialog_width')), int(self.browser.get('dialog_height'))))
        self.window.on_close = self._close_requested
        self.window.show()
        self.timer = owner.after(40, self._poll)

    def _close_requested(self):
        # Let the native close event finish before disposing of its window/context.
        self.cancelled = True
        return True

    def _poll(self):
        self.timer = None
        if self.finished:
            return
        state = self.browser.get('state')
        if self.cancelled or not self.window.is_open or state < 0:
            self._finish(None)
        elif state > 0:
            paths = list(self.browser.strs('result'))
            path = paths[0] if paths else None
            if path and self.kind == 'save' and self.extension and not Path(path).suffix:
                path += self.extension if self.extension.startswith('.') else '.'+self.extension
            self._finish(path)
        else:
            self.timer = self.owner.after(40, self._poll)

    def _finish(self, path, *, notify=True):
        if self.finished:
            return
        self.finished = True
        if self.timer is not None:
            self.owner.after_cancel(self.timer)
            self.timer = None
        self.window.close()
        if notify:
            self.on_result(path)

    def close(self):
        """The owner is closing: dispose of the child without a save callback."""
        self._finish(None, notify=False)

    def focus(self):
        self.window.wm('lift')
        self.window.wm('focus')
