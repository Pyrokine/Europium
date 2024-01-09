from typing import Union

from PySide6.QtCore import Signal, QMimeData
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from common import common, widget_base
from common.widget_base import MimeData
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

    def get_mime(self) -> QMimeData:
        mime = common.copy_mime_data(self.clipboard.mimeData(), customized=True)
        self.signalClipboardPaste.emit(mime)
        return mime

    def set_text(self, text: str) -> None:
        if isinstance(text, str):
            self.clipboard.setText(text)
        else:
            self.frame.logger.error('clipboard set text error, text type is {0}'.format(type(text)))

    def set_image(self, image: Union[QImage, QPixmap]) -> None:
        if isinstance(image, QImage):
            self.clipboard.setImage(image)
        elif isinstance(image, QPixmap):
            self.clipboard.setPixmap(image)
        else:
            self.frame.logger.error('clipboard set image error, image type is {0}'.format(type(image)))

    def set_mime(self, mime: QMimeData) -> None:
        if isinstance(mime, QMimeData):
            print(id(mime))
            self.clipboard.setMimeData(mime)
        else:
            self.frame.logger.error('clipboard set mime error, mime type is {0}'.format(type(mime)))

    @staticmethod
    def mime_generate_render_list(mime: MimeData) -> MimeData:
        if mime.hasText() and mime.text():
            mime.render_list.append(widget_base.RenderData(mime.text(), widget_base.RenderType.RENDER_TYPE_PLAIN_TEXT))

        if mime.hasImage() and mime.imageData():
            mime.render_list.append(widget_base.RenderData(mime.imageData(), widget_base.RenderType.RENDER_TYPE_QIMAGE))

        return mime
