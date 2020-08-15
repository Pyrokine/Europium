from PySide6.QtCore import QMimeData

from common import common, widget_base


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_parser')
        self.is_auto_start = True

        self.reset()

    @staticmethod
    def extract_text_image_from_mime_data(mime_data: QMimeData) -> dict:
        result = {
            'text': [],
            'image': [],
            'html': []
        }
        if mime_data.hasText() and mime_data.text():
            result['text'].append(mime_data.text())

        if mime_data.hasImage() and mime_data.imageData():
            result['image'].append(mime_data.imageData())

        if mime_data.hasHtml() and mime_data.html():
            result['html'].append(mime_data.html())

        return result
