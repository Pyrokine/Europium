import copy
import sys
from typing import Optional

from PySide6.QtCore import QSize, QPoint
from PySide6.QtGui import Qt, QMouseEvent

from common import common, widget_base
from widgets import widget_object_manager


class ResizeWindowButton(widget_base.Text):
    def __init__(self, obj: widget_base.Object):
        super().__init__(obj=obj,
                         pos=widget_base.RelativePos(lambda: QPoint(self.frame.width(), self.frame.height()), QPoint(-16, -16)),
                         text='↘',
                         size=QSize(15, 15),
                         is_changeable=False)

        self.move_and_show()

        self.last_frame_width = self.frame.width()
        self.last_frame_height = self.frame.height()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_start_pos = event.globalPos()
            self.last_global_pos = copy.deepcopy(self.global_pos)
            self.last_frame_width = self.frame.width()
            self.last_frame_height = self.frame.height()
            self.is_dragging = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.is_dragging:
            pos_diff = event.globalPos() - self.press_start_pos
            self.move_and_show()
            self.frame.resize(QSize(self.last_frame_width + pos_diff.x(), self.last_frame_height + pos_diff.y()))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
        super().mouseReleaseEvent(event)


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)
        self.setObjectName('widget_ui')
        self.is_auto_start = True

        self.obj: Optional[widget_base.Object] = None
        self.call_once = False

        self.reset()

    def enable_widget(self):
        if not self.call_once:
            self.call_once = True
            self.obj = widget_object_manager.Widget(self.frame).generate_object()

        self.add_resize_window()
        self.add_close_window()

    def add_resize_window(self):
        self.obj.add_object(ResizeWindowButton(self.obj))

    def add_close_window(self):
        self.obj.add_object(widget_base.Text(
            obj=self.obj,
            pos=widget_base.RelativePos(lambda: QPoint(self.frame.width(), 0), QPoint(-21, 1)),
            text='X',
            size=QSize(20, 20),
            is_changeable=False,
            func_select=widget_base.Func('', click_func=lambda x: sys.exit())
        ))
