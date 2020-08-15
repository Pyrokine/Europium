import copy

from PySide6.QtCore import QRect, QPoint, QSize
from PySide6.QtGui import Qt, QMouseEvent
from PySide6.QtWidgets import QRubberBand

from common import common, widget_base


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_drag_select')
        self.is_auto_start = True

        self.start_pos = QPoint()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, frame)
        self.is_dragging = False

        self.obj_idx_in_roi = set()
        self.last_obj_idx_in_roi = set()

        self.reset()

    def reset(self):
        self.start_pos = QPoint()
        self.rubber_band.close()
        self.is_dragging = False

        self.obj_idx_in_roi = set()
        self.last_obj_idx_in_roi = set()

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

    def on_mouse_press(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            for obj in self.frame.render_data.values():
                if common.is_point_a_in_rec_b(a_x=event.windowPos().x(),
                                              a_y=event.windowPos().y(),
                                              b_left=obj.global_pos_left,
                                              b_right=obj.global_pos_right,
                                              b_top=obj.global_pos_top,
                                              b_bottom=obj.global_pos_right):
                    return

            self.start_pos = event.windowPos()
            self.rubber_band.resize(QSize(0, 0))
            self.rubber_band.show()
            self.is_dragging = True

    def on_mouse_move(self, event: QMouseEvent) -> None:
        if self.is_dragging:
            pos_left = min(self.start_pos.x(), event.windowPos().x())
            pos_right = max(self.start_pos.x(), event.windowPos().x())
            pos_top = min(self.start_pos.y(), event.windowPos().y())
            pos_bottom = max(self.start_pos.y(), event.windowPos().y())

            obj_pos = self.frame.df_obj_pos[self.frame.df_obj_pos.apply(  # type:ignore
                lambda x: max(x['left'], pos_left) <= min(x['right'], pos_right) and max(x['top'], pos_top) <= min(x['bottom'], pos_bottom),
                axis=1)]

            if obj_pos.empty:
                self.obj_idx_in_roi.clear()
            else:
                self.obj_idx_in_roi = set(obj_pos['idx'])

                if event.windowPos().x() < self.start_pos.x():
                    self.obj_idx_in_roi = set(obj_idx for obj_idx in self.obj_idx_in_roi if common.is_rec_a_contain_b(
                        pos_left, pos_right, pos_top, pos_bottom,
                        self.frame.render_data[obj_idx].global_pos_left,
                        self.frame.render_data[obj_idx].global_pos_right,
                        self.frame.render_data[obj_idx].global_pos_top,
                        self.frame.render_data[obj_idx].global_pos_bottom,
                    ))

            for idx in self.obj_idx_in_roi - self.last_obj_idx_in_roi:
                self.frame.render_data[idx].pseudo_click()
            for idx in self.last_obj_idx_in_roi - self.obj_idx_in_roi:
                self.frame.render_data[idx].reset_pseudo_click()

            self.last_obj_idx_in_roi = copy.deepcopy(self.obj_idx_in_roi)

            self.rubber_band.setGeometry(QRect(QPoint(pos_left, pos_top), QPoint(pos_right, pos_bottom)))

    def on_mouse_release(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            for idx in self.obj_idx_in_roi:
                self.frame.render_data[idx].click()

            self.reset()
