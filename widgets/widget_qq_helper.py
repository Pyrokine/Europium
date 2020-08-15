import re

from PySide6.QtGui import QImage

from common import common, widget_base


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_qq_helper')
        self.is_auto_start = True

        self.reset()

    @staticmethod
    def extract_qq_image_from_text_image(text_image: dict) -> dict:
        for content in text_image['html']:
            for image_path in re.findall(re.compile(r'<img src=\"file:///(.+?)\">'), content):
                image = QImage(image_path)
                if image not in text_image['image']:  # TODO
                    text_image['image'].append(image)

        return text_image
