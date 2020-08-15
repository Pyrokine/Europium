from PySide6.QtCore import QPoint, QEvent

from common import common, widget_base, converter


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_render')
        self.is_auto_start = True

        self.frame.signalResize.connect(self.re_render_all)

        self.reset()

    def re_render_all(self, event: QEvent = None):
        for obj in self.frame.render_data.values():
            obj.move_and_show()

    def render_text_image(self, text_image: dict):
        obj: widget_base.Object = self.frame.widget_object_manager.generate_object()
        pos_x, pos_y = obj.global_pos.x(), obj.global_pos.y()

        if text_image['text']:
            for content in text_image['text']:
                text = obj.add_object(widget_base.Text(obj=obj, pos=QPoint(pos_x, pos_y), text=content))
                pos_y += text.height()

        if text_image['image']:
            for content in text_image['image']:
                image = obj.add_object(widget_base.Image(obj=obj, pos=QPoint(pos_x, pos_y), image=converter.qimage_to_qpixmap(content)))
                pos_y += image.height()
