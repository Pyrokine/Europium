from enum import Enum, unique, auto
from typing import Optional, Union, Dict

from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPixmap, QImage, QPainter
from PySide6.QtWidgets import QApplication, QGraphicsScene

from common import common, widget_base, converter, opencv_helper
from widgets import widget_clipboard, widget_shortcut


@unique
class GraphicsType(Enum):
    LINE = auto()
    RECT = auto()


class GraphicsAttr:
    def __init__(self, frame, scene: QGraphicsScene, graphics_type: GraphicsType):
        self.frame = frame
        self.scene = scene
        self.graphics_type = graphics_type

    def generate_graphics_item(self, start_pos) -> Union[
        widget_base.GraphicsLineItem,
        widget_base.GraphicsRectItem]:
        if self.graphics_type == GraphicsType.LINE:
            return widget_base.GraphicsLineItem(
                frame=self.frame,
                scene=self.scene,
                pos_start=start_pos,
                pos_end=start_pos,
                selectable=True,
                movable=True,
                accept_hover=True,
                enable_handle=True)
        elif self.graphics_type == GraphicsType.RECT:
            return widget_base.GraphicsRectItem(
                frame=self.frame,
                scene=self.scene,
                rect=QRect(start_pos, start_pos),
                selectable=True,
                movable=True,
                accept_hover=True,
                enable_handle=True)

    @staticmethod
    def get_cursor_shape() -> Qt.CursorShape:
        return Qt.CursorShape.CrossCursor


class ScreenshotFrame(widget_base.Frame):
    def __init__(self, _widget_clipboard: widget_clipboard.Widget, screenshot: QPixmap):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.BypassWindowManagerHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.showFullScreen()

        self.widget_clipboard = _widget_clipboard

        self.screenshot = screenshot
        background = converter.qpixmap_to_numpy_bgr(screenshot)
        background = opencv_helper.change_rgb_image_brightness(background, -30)
        self.background = converter.numpy_bgr_to_qpixmap(background)

        self.move(QPoint())
        self.resize(QSize(800, 600))
        self.setScene(QGraphicsScene(QRect(QPoint(), screenshot.size())))

        widget_base.GraphicsPixmapItem(
            frame=self,
            scene=self.scene(),
            rect=self.background.rect(),
            pixmap=self.background,
            selectable=False,
            movable=False,
            accept_hover=False,
            enable_handle=False)

        self.start_pos = QPoint()
        self.is_dragging = False

        self.roi_rect: Optional[widget_base.GraphicsPixmapItem] = None
        self.roi_selected: bool = False
        self.cur_graphics_type: Optional[GraphicsType] = None
        self.cur_graphics_item: Optional[Union[
            widget_base.GraphicsLineItem,
            widget_base.GraphicsRectItem]
        ] = None

        self.graphics_attr: Dict[GraphicsType, GraphicsAttr] = {
            GraphicsType.LINE: GraphicsAttr(
                frame=self,
                scene=self.scene(),
                graphics_type=GraphicsType.LINE
            ),
            GraphicsType.RECT: GraphicsAttr(
                frame=self,
                scene=self.scene(),
                graphics_type=GraphicsType.RECT
            )
        }

    def reset(self):
        self.scene().clear()
        widget_base.GraphicsPixmapItem(
            frame=self,
            scene=self.scene(),
            rect=self.background.rect(),
            pixmap=self.background,
            selectable=False,
            movable=False,
            accept_hover=False,
            enable_handle=False)

        self.roi_rect = None
        self.roi_selected = False
        self.cur_graphics_item = None
        self.cursor_shape_stack = [Qt.CursorShape.ArrowCursor]

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            if self.roi_selected:
                self.reset()
            else:
                self.close()
        elif self.roi_selected:
            if key == Qt.Key.Key_Return:
                scene_bounding_rect = self.roi_rect.sceneBoundingRect()
                final_screenshot = QImage(scene_bounding_rect.size().toSize(), QImage.Format.Format_ARGB32_Premultiplied)
                painter = QPainter(final_screenshot)
                self.scene().render(painter, target=final_screenshot.rect(), source=scene_bounding_rect)
                painter.end()
                self.widget_clipboard.set_image(final_screenshot)
                self.close()
            if key == Qt.Key.Key_L:
                self.cur_graphics_type = GraphicsType.LINE
                self.add_cursor_shape(self.graphics_attr[self.cur_graphics_type].get_cursor_shape())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPos()
            self.is_dragging = True

            if not self.roi_selected:
                self.roi_rect = widget_base.GraphicsPixmapItem(
                    frame=self,
                    scene=self.scene(),
                    rect=QRect(),
                    pixmap=self.screenshot,
                    selectable=True,
                    movable=True,
                    accept_hover=True,
                    enable_handle=True)
            else:
                if self.cur_graphics_type:
                    self.roi_rect.set_movable(False)
                    self.cur_graphics_item = self.graphics_attr[self.cur_graphics_type].generate_graphics_item(self.start_pos)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.is_dragging:
            if not self.roi_selected:
                self.roi_rect.update_all_pos(
                    top_left=self.start_pos,
                    bottom_right=event.globalPos()
                )
            elif self.cur_graphics_item:
                self.cur_graphics_item.update_all_pos(
                    pos_start=self.start_pos,
                    pos_end=event.globalPos()
                )

            self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.is_dragging = False

        if not self.roi_selected:
            self.roi_selected = True
        elif self.cur_graphics_type:
            self.roi_rect.set_movable(True)
            self.cur_graphics_type = None
            self.cur_graphics_item = None
            self.remove_cursor_shape()

        super().mouseReleaseEvent(event)


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_screenshot')
        self.is_auto_start = True

        self.widget_clipboard: widget_clipboard.Widget = widget_clipboard.Widget(frame)

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='capture screen',
                                                 shortcut_key=['Ctrl', 'Alt', 'Q'],
                                                 callback=self.capture_screen)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.painter = None

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def capture_screen(self):
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0)

        ScreenshotFrame(self.widget_clipboard, screenshot)

        # screenshot.save('screenshot.png')
