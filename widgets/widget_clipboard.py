from typing import Union

from PySide6.QtCore import Signal, QMimeData
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from common import common, widget_base
from widgets import widget_shortcut


@common.singleton
class Widget(widget_base.WidgetBase):
    signalClipboardPaste = Signal(object)

    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_clipboard')
        self.is_auto_start = True

        self.clipboard = QApplication.clipboard()

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='get mime from clipboard',
                                                 shortcut_key=['Ctrl', 'V'],
                                                 callback=self.get_mime)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def get_mime(self):
        mime = self.clipboard.mimeData()
        self.frame.mime_data.update({
            self.frame.mime_idx: {
                'idx': self.frame.mime_idx,
                'pos': self.frame.get_cursor_global_pos(),
                'mime': mime
            }
        })
        self.signalClipboardPaste.emit(self.frame.mime_idx)
        self.frame.mime_idx += 1

    def set_text(self, text: str):
        if isinstance(text, str):
            self.clipboard.setText(text)
        else:
            self.frame.logger.error('clipboard set text error, text type is {0}'.format(type(text)))

    def set_image(self, image: Union[QImage, QPixmap]):
        if isinstance(image, QImage):
            self.clipboard.setImage(image)
        elif isinstance(image, QPixmap):
            self.clipboard.setPixmap(image)
        else:
            self.frame.logger.error('clipboard set image error, image type is {0}'.format(type(image)))

    def set_mime(self, mime: QMimeData):
        if isinstance(mime, QMimeData):
            self.clipboard.setMimeData(mime)
        else:
            self.frame.logger.error('clipboard set mime error, mime type is {0}'.format(type(mime)))
