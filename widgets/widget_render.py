from typing import List

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

    def re_render_all(self, event: QEvent = None) -> None:
        for obj in self.frame.render_data.values():
            obj.move_and_show()

    def render_to_frame(self, data) -> None:
        if not hasattr(data, 'render_list'):
            self.frame.logger.error('data has no render_list')
            return

        obj: widget_base.Object = self.frame.widget_object_manager.generate_object()
        pos_x, pos_y = obj.global_pos.x(), obj.global_pos.y()

        render_list: List[widget_base.RenderData] = data.render_list
        for render_data in render_list:
            if render_data.render_type == widget_base.RenderType.RENDER_TYPE_PLAIN_TEXT:
                text = obj.add_object(widget_base.Text(obj=obj,
                                                       pos=QPoint(pos_x, pos_y),
                                                       text=render_data.content))
                pos_y += text.height()
            elif render_data.render_type == widget_base.RenderType.RENDER_TYPE_QIMAGE:
                image = obj.add_object(widget_base.Image(obj=obj,
                                                         pos=QPoint(pos_x, pos_y),
                                                         image=converter.qimage_to_qpixmap(render_data.content)))
                pos_y += image.height()
            else:
                self.frame.logger.warning('unrecognized render type')
