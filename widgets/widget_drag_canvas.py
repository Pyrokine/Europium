import copy

from PySide6.QtCore import QPoint
from PySide6.QtGui import Qt, QMouseEvent

from common import common, widget_base
from widgets import widget_render


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_drag_canvas')
        self.is_auto_start = True

        self.start_pos = QPoint()
        self.last_coordinate_offset = copy.deepcopy(self.frame.coordinate_offset)
        self.last_frame_pos = self.frame.geometry().topLeft()

        self.is_dragging_canvas = False
        self.is_moving_frame = False

        self.widget_render: widget_render.Widget = widget_render.Widget(frame)

        self.reset()

    def reset(self) -> None:
        self.is_dragging_canvas = False
        self.is_moving_frame = False
        self.frame.is_self_moving = False

    def enable_widget(self) -> None:
        super().enable_widget()
        self.frame.signalMousePress.connect(self.on_mouse_press)
        self.frame.signalMouseMove.connect(self.on_mouse_move)
        self.frame.signalMouseRelease.connect(self.on_mouse_release)

    def disable_widget(self) -> None:
        super().disable_widget()
        self.frame.signalMousePress.disconnect(self.on_mouse_press)
        self.frame.signalMouseMove.disconnect(self.on_mouse_move)
        self.frame.signalMouseRelease.disconnect(self.on_mouse_release)

    def on_mouse_press(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self.start_pos = event.globalPos()
            self.last_coordinate_offset = copy.deepcopy(self.frame.coordinate_offset)
            self.is_dragging_canvas = True
            self.frame.is_self_moving = True
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.start_pos = event.globalPos()
            self.last_frame_pos = self.frame.geometry().topLeft()
            self.is_moving_frame = True
            self.frame.is_self_moving = True

    def on_mouse_move(self, event: QMouseEvent):
        if self.is_dragging_canvas:
            pos_diff = event.globalPos() - self.start_pos
            self.frame.coordinate_offset = self.last_coordinate_offset + pos_diff
            self.widget_render.re_render_all()
        elif self.is_moving_frame:
            pos_diff = event.globalPos() - self.start_pos
            self.frame.move(self.last_frame_pos + pos_diff)
            self.widget_render.re_render_all()

    def on_mouse_release(self, event: QMouseEvent):
        self.reset()
