import copy
import importlib
import os
import traceback
from enum import Enum, unique, auto
from typing import List, Dict, Set, Union, Callable, TypedDict, Optional, Any, cast

import loguru
from PySide6.QtCore import Signal, Qt, QSize, QPoint, QRect, QPointF
from PySide6.QtGui import (QImage, QPixmap, QCursor, QKeyEvent, QMouseEvent, QPaintEvent, QFontMetrics, QAction, QContextMenuEvent,
                           QPainter, QResizeEvent)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (QWidget, QPushButton, QTreeWidget, QTreeWidgetItem, QTableWidget, QTabWidget, QCheckBox, QLineEdit,
                               QPlainTextEdit, QHeaderView, QAbstractItemView, QGraphicsItem, QGraphicsScene, QGraphicsView,
                               QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem, QMenu, QGraphicsRectItem,
                               QGraphicsSceneHoverEvent, QGraphicsObject, QStyleOptionGraphicsItem)

# noinspection PyUnresolvedReferences
import pipeline
# noinspection PyUnresolvedReferences
import widgets

from config import Config
from common import common


####################################################################################################
# Frame
####################################################################################################


class Frame(QGraphicsView):
    signalKeyPress = Signal(object)
    signalMousePress = Signal(object)
    signalMouseMove = Signal(object)
    signalMouseRelease = Signal(object)
    signalResize = Signal(object)

    def __init__(self,
                 size: QSize = QSize(1400, 800),
                 is_import_module: bool = False):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.BypassWindowManagerHint |
            Qt.WindowType.NoDropShadowWindowHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet('background-color: {0};'.format(Config.Main().background_color))

        self.coordinate_offset = QPoint()
        self.setScene(QGraphicsScene(self.rect()))
        self.resize(size)

        self.mime_data = {}
        self.mime_idx = 0
        self.render_data = {}  # idx -> obj, store all the data needed to be rendered
        self.render_idx = 0  # play the role as uuid
        self.widgets = {}
        self.pipeline = {}
        self.cursor_shape_stack = [Qt.CursorShape.ArrowCursor]

        self.parent_object = None
        self.children_objects: Set['Object'] = set()

        self.is_self_moving = False

        self.logger = loguru.logger
        self.logger.add('log/{0}.log'.format(common.Time().date_and_time2))

        self.is_import_module = is_import_module
        self.widget_object_manager = None
        self.widget_drag_select = None
        if is_import_module:
            self.import_modules()

    def import_modules(self):
        for module_folder, class_name in zip(['widgets', 'pipeline'], ['Widget', 'Pipeline']):
            for module_filename in os.listdir(module_folder):
                module_name, ext = os.path.splitext(module_filename)
                if os.path.isfile(common.join_path(module_folder, module_filename)) and ext == '.py':
                    importlib.import_module('{0}.{1}'.format(module_folder, module_name))
                    try:
                        exec(
                            'if "{2}" in dir({0}.{1}):\n'
                            '    module = {0}.{1}.{2}(self)\n'
                            '    if module.objectName() in self.{0}:\n'
                            '        self.logger.error("{1} has already been registered")\n'
                            '    else:\n'
                            '        self.{0}.update({{module.objectName(): module}})\n'
                            '        self.logger.success("{1} registration successful")'
                            .format(module_folder, module_name, class_name))
                    except Exception as e:
                        self.logger.error(e)
                        self.logger.error(traceback.format_exc())

        self.widget_object_manager = self.load_widget(self, 'widget_object_manager')
        self.widget_drag_select = self.load_widget(self, 'widget_drag_select')

        for _module in [*self.widgets.values(), *self.pipeline.values()]:
            _module.auto_start()

    def resize(self, arg__1) -> None:
        if isinstance(arg__1, QSize):
            self.scene().setSceneRect(QRect(QPoint(0, 0), arg__1))
        else:
            self.logger.error('only support QSize')
        super().resize(arg__1)

    def global_pos_to_relative_pos(self, pos: QPoint) -> QPoint:
        return pos + self.coordinate_offset

    def relative_pos_to_global_pos(self, pos: QPoint) -> QPoint:
        return pos - self.coordinate_offset

    def get_cursor_relative_pos(self) -> QPoint:
        return QPoint(QCursor().pos().x() - self.geometry().x(), QCursor().pos().y() - self.geometry().y())

    def get_cursor_global_pos(self) -> QPoint:
        return self.relative_pos_to_global_pos(self.get_cursor_relative_pos())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self.signalKeyPress.emit(event)
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.signalMousePress.emit(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.signalMouseMove.emit(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.signalMouseRelease.emit(event)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.signalResize.emit(event)
        super().resizeEvent(event)

    def add_cursor_shape(self, cursor_shape: Qt.CursorShape) -> None:
        self.cursor_shape_stack.append(cursor_shape)
        self.setCursor(self.cursor_shape_stack[-1])

    def remove_cursor_shape(self) -> None:
        self.cursor_shape_stack.pop(-1)
        self.setCursor(self.cursor_shape_stack[-1])

    def add_object(self, obj: 'Object') -> Any:
        self.widget_object_manager.add_to_render_data(obj)
        self.children_objects.add(obj)
        return obj

    def remove_object(self, obj: 'Object') -> None:
        if obj in self.children_objects:
            self.children_objects.remove(obj)
            self.widget_object_manager.remove_from_render_data(obj)
        else:
            self.logger.error('failed to remove object, render_idx = {0}'.format(obj.render_idx))

    def remove_all_objects(self) -> None:
        for obj in self.children_objects:
            obj.remove_all_objects()

    def load_widget(self, this_widget: QWidget, target_widget: str) -> Optional[QWidget]:
        if self.is_import_module:
            if target_widget in self.widgets:
                return self.widgets[target_widget]
            else:
                self.logger.error('{0}: cannot find widget [{1}]'.format(this_widget.objectName(), target_widget))
                return None
        else:
            self.logger.warning('this frame does not manage the widgets')

    def generate_webview(self) -> QWebEngineView:
        return QWebEngineView(self)


####################################################################################################
# Object
####################################################################################################


class RelativePos:
    def __init__(self, ref: Callable, relative_pos: QPoint):
        self.ref = ref
        self.relative_pos = relative_pos

    def get_global_pos(self) -> QPoint:
        return self.ref() + self.relative_pos

    def update_relative_pos(self, global_pos) -> None:
        self.relative_pos = global_pos - self.ref()


class Action(QAction):
    def __init__(self,
                 menu: QMenu,
                 text: str,
                 func: 'Func',
                 icon: QPixmap = None):
        super().__init__(text=text, parent=menu)

        self.func = func

        if icon:
            self.setIcon(icon)

        self.triggered.connect(func.click_func)


class SubObjectMenu(QMenu):
    def __init__(self,
                 sub_obj: 'SubObject'):
        super().__init__(sub_obj)  # type: ignore

        self.sub_obj = sub_obj

        self.addAction(Action(
            menu=self,
            text='Change Size',
            func=Func('Change Size',
                      click_func=lambda: (self.sub_obj.bounding_rect.hide()
                                          if self.sub_obj.bounding_rect.isVisible()
                                          else self.sub_obj.bounding_rect.show()))
        ))

        self.addAction(Action(
            menu=self,
            text='Delete',
            func=Func('Delete',
                      click_func=lambda: self.sub_obj.deleteLater())
        ))


class SubObject:
    def __init__(self,
                 obj: Union['SubObject', 'EmbeddedObject', 'Object'],
                 pos: Union[QPoint, RelativePos],
                 size: QSize = None):
        self.frame: Frame = obj.frame

        self.parent_object = obj
        self.children_objects: Set[Union['SubObject', 'EmbeddedObject']] = set()

        self.render_idx = None
        self.is_show = True
        self.is_delete = False

        if size:
            self.resize(size)  # type: ignore

        self.global_pos = QPoint()
        self.relative_pos = None
        if isinstance(pos, QPoint):
            self.global_pos: QPoint = pos
        elif isinstance(pos, RelativePos):
            self.relative_pos: RelativePos = pos
        else:
            self.frame.logger.error('unrecognized pos type: {}'.format(type(pos)))
            return

        self.is_self_moving = common.ToggleBool()
        self.bounding_rect = GraphicsRectItem(frame=self.frame,
                                              scene=self.frame.scene(),
                                              rect=QRect(),
                                              selectable=True,
                                              movable=True,
                                              accept_hover=True,
                                              enable_handle=True)
        self.bounding_rect.handle_top_left.signalPositionChange.connect(lambda x: self.on_handle_move())
        self.bounding_rect.handle_top_right.signalPositionChange.connect(lambda x: self.on_handle_move())
        self.bounding_rect.handle_bottom_left.signalPositionChange.connect(lambda x: self.on_handle_move())
        self.bounding_rect.handle_bottom_right.signalPositionChange.connect(lambda x: self.on_handle_move())
        self.bounding_rect.hide()

        self.menu = SubObjectMenu(self)

        self.move_and_show()

        self.global_pos_left = self.global_pos.x()
        self.global_pos_right = self.global_pos.x() + self.width()  # type: ignore
        self.global_pos_top = self.global_pos.y()
        self.global_pos_bottom = self.global_pos.y() + self.height()  # type: ignore

    def deleteLater(self) -> None:  # noqa
        if self.is_delete:
            return
        else:
            self.is_delete = True
            self.bounding_rect.deleteLater()
            self.frame.scene().removeItem(self.bounding_rect)
            self.parent_object.remove_object(self)
            super().deleteLater()

    def reset(self) -> None:
        pass

    def click(self) -> None:
        pass

    def pseudo_click(self) -> None:
        pass

    def reset_pseudo_click(self) -> None:
        pass

    def move_and_show(self) -> None:
        with self.is_self_moving:
            if self.relative_pos:
                new_pos = self.relative_pos.get_global_pos()
                self.global_pos = new_pos
            else:
                new_pos = self.global_pos + self.frame.coordinate_offset
            self.move(new_pos)  # type: ignore
            self.bounding_rect.update_all_pos(top_left=QPoint(new_pos.x() - 2, new_pos.y() - 2),
                                              bottom_right=QPoint(new_pos.x() + self.width() + 2,  # type: ignore
                                                                  new_pos.y() + self.height() + 2))  # type: ignore

            if self.is_show:
                self.show()
            else:
                self.hide()

    def show(self) -> None:
        super().show()
        self.is_show = True

    def hide(self) -> None:
        super().hide()
        self.is_show = False
        self.bounding_rect.hide()

    def add_object(self, obj: Union['SubObject', 'EmbeddedObject', 'Object']) -> Any:
        self.frame.widget_object_manager.add_to_render_data(obj)
        self.children_objects.add(obj)
        obj.parent_object = self

        return obj

    def remove_object(self, obj: Union['SubObject', 'EmbeddedObject', 'Object']) -> None:
        if obj in self.children_objects:
            self.children_objects.remove(obj)
            self.frame.widget_object_manager.remove_from_render_data(obj)
        else:
            self.frame.logger.error('failed to remove object, render_idx = {0}'.format(obj.render_idx))

    def remove_all_objects(self) -> None:
        for obj in self.children_objects:
            obj.remove_all_objects()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa
        self.menu.exec(event.globalPos())
        super().contextMenuEvent(event)

    def on_handle_move(self) -> None:
        if not self.frame.is_self_moving and not self.is_self_moving:
            new_pos = self.bounding_rect.pos_handle_top_left + QPoint(2, 2)
            self.update_global_pos(self.frame.relative_pos_to_global_pos(new_pos))

            self.move(new_pos)  # type: ignore
            self.resize_bounding_rect(self.bounding_rect.rect().size().toSize() - QSize(2, 2))

    def resize_bounding_rect(self, size: QSize) -> None:
        self.resize(size)  # type: ignore

    def update_global_pos(self, global_pos) -> None:
        self.global_pos = copy.deepcopy(global_pos)
        if self.relative_pos:
            self.relative_pos.update_relative_pos(self.global_pos)

        self.global_pos_left, self.global_pos_top = self.global_pos.toTuple()
        self.global_pos_right = self.global_pos_left + self.width()  # type: ignore
        self.global_pos_bottom = self.global_pos_top + self.height()  # type: ignore


class EmbeddedObject:
    def __init__(self,
                 obj: Union['EmbeddedObject', 'Object'],
                 size: QSize = None):
        self.frame: Frame = obj.frame

        self.parent_object = obj
        self.children_objects: Set[Union[SubObject, 'EmbeddedObject']] = set()

        self.render_idx = None
        self.is_show = True
        self.is_delete = False

        if size:
            self.resize(size)  # type: ignore

    def deleteLater(self) -> None:  # noqa
        if self.is_delete:
            return
        else:
            self.is_delete = True
            self.parent_object.remove_object(self)
            super().deleteLater()

    def add_object(self, obj: Union[SubObject, 'EmbeddedObject', 'Object']) -> Any:
        self.frame.widget_object_manager.add_to_render_data(obj)
        self.children_objects.add(obj)
        obj.parent_object = self

        return obj

    def remove_object(self, obj: Union[SubObject, 'EmbeddedObject', 'Object']) -> None:
        if obj in self.children_objects:
            self.children_objects.remove(obj)
            self.frame.widget_object_manager.remove_from_render_data(obj)
        else:
            self.frame.logger.error('failed to remove object, render_idx = {0}'.format(obj.render_idx))

    def remove_all_objects(self) -> None:
        for obj in self.children_objects:
            obj.remove_all_objects()


class Object(QWidget):
    def __init__(self,
                 frame: Frame,
                 pos: Union[QPoint, RelativePos],
                 render_idx: int):
        super().__init__(None)

        self.setObjectName('base_object')
        self.frame = frame
        self.render_idx = render_idx

        if isinstance(pos, QPoint):
            self.global_pos: QPoint = pos
        elif isinstance(pos, RelativePos):
            self.relative_pos: RelativePos = pos
        else:
            self.frame.logger.error('unrecognized pos type: {}'.format(type(pos)))
            return

        self.is_show = False
        self.is_delete = False

        self.move_and_show()

        self.parent_object = frame
        self.children_objects: Set[Union['SubObject', 'EmbeddedObject']] = set()

        self.global_pos_left = self.global_pos.x()
        self.global_pos_right = self.global_pos.x()
        self.global_pos_top = self.global_pos.y()
        self.global_pos_bottom = self.global_pos.y()

    def deleteLater(self) -> None:
        if self.is_delete:
            return
        else:
            self.is_delete = True
            self.remove_all_objects()
            super().deleteLater()

    def reset(self) -> None:
        pass

    def move_and_show(self) -> None:
        pass

    def click(self) -> None:
        pass

    def pseudo_click(self) -> None:
        pass

    def reset_pseudo_click(self) -> None:
        pass

    def add_object(self, obj: Union[SubObject, EmbeddedObject, 'Object']) -> Any:
        self.frame.widget_object_manager.add_to_render_data(obj)
        self.children_objects.add(obj)
        obj.parent_object = self

        return obj

    def remove_object(self, obj: Union[SubObject, EmbeddedObject, 'Object']) -> None:
        if obj in self.children_objects:
            self.children_objects.remove(obj)
            self.frame.widget_object_manager.remove_from_render_data(obj)
        else:
            self.frame.logger.error('failed to remove widget, render_idx = {0}'.format(obj.render_idx))

    def remove_all_objects(self) -> None:
        for obj in self.children_objects:
            obj.remove_all_objects()

    def update_global_pos(self, global_pos) -> None:
        self.global_pos = copy.deepcopy(global_pos)
        if self.relative_pos:
            self.relative_pos.update_relative_pos(self.global_pos)

        self.global_pos_left, self.global_pos_top = self.global_pos.toTuple()
        self.global_pos_right = self.global_pos_left + self.width()  # type: ignore
        self.global_pos_bottom = self.global_pos_top + self.height()  # type: ignore


####################################################################################################
# Graphics
####################################################################################################


class GraphicsHandle(QGraphicsObject):
    signalPositionChange = Signal(QPointF)

    def __init__(self,
                 frame: Frame,
                 pos: QPoint,
                 cursor_shape: Qt.CursorShape = Qt.CursorShape.SizeAllCursor):
        super().__init__()

        self.frame = frame
        self.cursor_shape = cursor_shape

        self.rect = QRect(pos.x() - 4, pos.y() - 4, 8, 8)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.add_cursor_shape(self.cursor_shape)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.remove_cursor_shape()
        super().hoverLeaveEvent(event)

    def boundingRect(self) -> QRect:
        return self.rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = ...) -> None:
        painter.drawRect(self.rect)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            if self.frame.widget_drag_select:
                self.frame.widget_drag_select.reset()
            self.signalPositionChange.emit(value)
        return super().itemChange(change, value)


class GraphicsRectItem(QGraphicsRectItem):
    def __init__(self,
                 frame: Frame,
                 scene: QGraphicsScene,
                 rect: QRect,
                 selectable: bool = False,
                 movable: bool = False,
                 accept_hover: bool = False,
                 enable_handle: bool = False):
        super().__init__(rect)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, selectable)
        self.set_movable(movable)
        self.setAcceptHoverEvents(accept_hover)

        self.frame = frame
        self.scene = scene

        self.pos_handle_top_left = rect.topLeft()
        self.pos_handle_top_right = rect.topRight()
        self.pos_handle_bottom_left = rect.bottomLeft()
        self.pos_handle_bottom_right = rect.bottomRight()
        self.pos_item_change = QPointF()

        self.handle_top_left = GraphicsHandle(frame, pos=self.pos().toPoint(), cursor_shape=Qt.CursorShape.SizeFDiagCursor)
        self.handle_top_right = GraphicsHandle(frame, pos=self.pos().toPoint(), cursor_shape=Qt.CursorShape.SizeBDiagCursor)
        self.handle_bottom_left = GraphicsHandle(frame, pos=self.pos().toPoint(), cursor_shape=Qt.CursorShape.SizeBDiagCursor)
        self.handle_bottom_right = GraphicsHandle(frame, pos=self.pos().toPoint(), cursor_shape=Qt.CursorShape.SizeFDiagCursor)

        self.scene.addItem(self)
        self.enable_handle = enable_handle
        self.is_handle_moving = common.ToggleBool()

        if enable_handle:
            self.scene.addItem(self.handle_top_left)
            self.scene.addItem(self.handle_top_right)
            self.scene.addItem(self.handle_bottom_left)
            self.scene.addItem(self.handle_bottom_right)

            self.hide_handles()

            self.handle_top_left.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'top_left'))
            self.handle_top_right.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'top_right'))
            self.handle_bottom_left.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'bottom_left'))
            self.handle_bottom_right.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'bottom_right'))

    def deleteLater(self) -> None:  # noqa
        self.scene.removeItem(self)
        self.scene.removeItem(self.handle_top_left)
        self.scene.removeItem(self.handle_top_right)
        self.scene.removeItem(self.handle_bottom_left)
        self.scene.removeItem(self.handle_bottom_right)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.add_cursor_shape(Qt.CursorShape.UpArrowCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.remove_cursor_shape()
        super().hoverLeaveEvent(event)

    def update_rect_pos(self, top_left: QPoint, bottom_right: QPoint) -> None:
        self.pos_handle_top_left = copy.deepcopy(top_left)
        self.pos_handle_top_right = QPoint(bottom_right.x(), top_left.y())
        self.pos_handle_bottom_left = QPoint(top_left.x(), bottom_right.y())
        self.pos_handle_bottom_right = copy.deepcopy(bottom_right)

        self.setRect(top_left.x() - self.pos_item_change.x(),
                     top_left.y() - self.pos_item_change.y(),
                     bottom_right.x() - top_left.x(),
                     bottom_right.y() - top_left.y())

    def update_handle_pos(self, top_left: QPoint, bottom_right: QPoint) -> None:
        if self.enable_handle:
            with self.is_handle_moving:
                self.pos_handle_top_left = copy.deepcopy(top_left)
                self.pos_handle_top_right = QPoint(bottom_right.x(), top_left.y())
                self.pos_handle_bottom_left = QPoint(top_left.x(), bottom_right.y())
                self.pos_handle_bottom_right = copy.deepcopy(bottom_right)

                self.handle_top_left.setPos(self.pos_handle_top_left)
                self.handle_top_right.setPos(self.pos_handle_top_right)
                self.handle_bottom_left.setPos(self.pos_handle_bottom_left)
                self.handle_bottom_right.setPos(self.pos_handle_bottom_right)

    def update_all_pos(self, top_left: QPoint, bottom_right: QPoint) -> None:
        top_left_ = QPoint(min(top_left.x(), bottom_right.x()), min(top_left.y(), bottom_right.y()))
        bottom_right_ = QPoint(max(top_left.x(), bottom_right.x()), max(top_left.y(), bottom_right.y()))

        self.update_rect_pos(top_left_, bottom_right_)
        self.update_handle_pos(top_left_, bottom_right_)

    def on_handle_move(self, pos: QPoint, point: str) -> None:
        if not self.is_handle_moving:
            if point == 'top_left':
                self.update_all_pos(pos, self.pos_handle_bottom_right)
            elif point == 'top_right':
                self.update_all_pos(QPoint(self.pos_handle_top_left.x(), pos.y()),
                                    QPoint(pos.x(), self.pos_handle_bottom_right.y()))
            elif point == 'bottom_left':
                self.update_all_pos(QPoint(pos.x(), self.pos_handle_top_left.y()),
                                    QPoint(self.pos_handle_bottom_right.x(), pos.y()))
            elif point == 'bottom_right':
                self.update_all_pos(self.pos_handle_top_left, pos)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            pos_diff = (value - self.pos_item_change).toPoint()
            self.pos_item_change = value
            self.update_handle_pos(self.pos_handle_top_left + pos_diff, self.pos_handle_bottom_right + pos_diff)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value or (
                    self.handle_top_left.isUnderMouse() or
                    self.handle_top_right.isUnderMouse() or
                    self.handle_bottom_left.isUnderMouse() or
                    self.handle_bottom_right.isUnderMouse()
            ):
                self.show_handles()
            else:
                self.hide_handles()

        return super().itemChange(change, value)

    def show_handles(self) -> None:
        self.handle_top_left.show()
        self.handle_top_right.show()
        self.handle_bottom_left.show()
        self.handle_bottom_right.show()

    def hide_handles(self) -> None:
        self.handle_top_left.hide()
        self.handle_top_right.hide()
        self.handle_bottom_left.hide()
        self.handle_bottom_right.hide()

    def show(self) -> None:
        super().show()
        self.show_handles()

    def hide(self) -> None:
        super().hide()
        self.hide_handles()

    def set_movable(self, movable: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, movable)


class GraphicsPixmapItem(GraphicsRectItem):
    def __init__(self,
                 frame: Frame,
                 scene: QGraphicsScene,
                 rect: QRect,
                 pixmap: QPixmap,
                 selectable: bool = False,
                 movable: bool = False,
                 accept_hover: bool = False,
                 enable_handle: bool = False):
        GraphicsRectItem.__init__(self, frame, scene, rect, selectable, movable, accept_hover, enable_handle)

        self.frame = frame
        self.pixmap = pixmap

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        super().hoverEnterEvent(event)
        self.frame.add_cursor_shape(Qt.CursorShape.OpenHandCursor)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        super().hoverLeaveEvent(event)
        self.frame.remove_cursor_shape()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = ...) -> None:
        painter.drawPixmap(self.rect().toRect(),
                           self.pixmap,
                           QRect((self.rect().topLeft() + self.pos_item_change).toPoint(), self.rect().size().toSize()))


class GraphicsLineItem(QGraphicsLineItem):
    def __init__(self,
                 frame: Frame,
                 scene: QGraphicsScene,
                 pos_start: QPoint,
                 pos_end: QPoint,
                 selectable: bool = False,
                 movable: bool = False,
                 accept_hover: bool = False,
                 enable_handle: bool = False):
        super().__init__(pos_start.x(), pos_start.y(), pos_end.x(), pos_end.y())

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, selectable)
        self.set_movable(movable)
        self.setAcceptHoverEvents(accept_hover)

        self.frame = frame
        self.scene = scene

        self.pos_handle_start = copy.deepcopy(pos_start)
        self.pos_handle_end = copy.deepcopy(pos_end)
        self.pos_item_change = QPointF()

        self.handle_start = GraphicsHandle(frame=frame, pos=self.pos().toPoint())
        self.handle_end = GraphicsHandle(frame=frame, pos=self.pos().toPoint())

        self.scene.addItem(self)
        self.enable_handle = enable_handle
        self.is_handle_moving = common.ToggleBool()

        if enable_handle:
            self.scene.addItem(self.handle_start)
            self.scene.addItem(self.handle_end)

            self.handle_start.hide()
            self.handle_end.hide()

            self.handle_start.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'start'))
            self.handle_end.signalPositionChange.connect(lambda x: self.on_handle_move(x.toPoint(), 'end'))

    def deleteLater(self) -> None:  # noqa
        self.scene.removeItem(self)
        self.scene.removeItem(self.pos_handle_start)
        self.scene.removeItem(self.pos_handle_end)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.add_cursor_shape(Qt.CursorShape.UpArrowCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.frame.remove_cursor_shape()
        super().hoverLeaveEvent(event)

    def update_line_pos(self, pos_start: QPoint, pos_end: QPoint) -> None:
        self.pos_handle_start = pos_start
        self.pos_handle_end = pos_end

        self.setLine(pos_start.x() - self.pos_item_change.x(),
                     pos_start.y() - self.pos_item_change.y(),
                     pos_end.x() - self.pos_item_change.x(),
                     pos_end.y() - self.pos_item_change.y())

    def update_handle_pos(self, pos_handle_start: QPoint, pos_handle_end: QPoint) -> None:
        if self.enable_handle:
            with self.is_handle_moving:
                self.pos_handle_start = pos_handle_start
                self.pos_handle_end = pos_handle_end

                self.handle_start.setPos(pos_handle_start.x(), pos_handle_start.y())
                self.handle_end.setPos(pos_handle_end.x(), pos_handle_end.y())

    def update_all_pos(self, pos_start: QPoint, pos_end: QPoint) -> None:
        self.update_line_pos(pos_start, pos_end)
        self.update_handle_pos(pos_start, pos_end)

    def on_handle_move(self, pos: QPoint, point: str) -> None:
        if not self.is_handle_moving:
            if point == 'start':
                self.update_line_pos(pos, self.pos_handle_end)
            elif point == 'end':
                self.update_line_pos(self.pos_handle_start, pos)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            pos_diff = (value - self.pos_item_change).toPoint()
            self.pos_item_change = value
            self.update_handle_pos(self.pos_handle_start + pos_diff, self.pos_handle_end + pos_diff)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value or (
                    self.handle_start.isUnderMouse() or
                    self.handle_end.isUnderMouse()
            ):
                self.show_handles()
            else:
                self.hide_handles()

        return super().itemChange(change, value)

    def show_handles(self) -> None:
        self.handle_start.show()
        self.handle_end.show()

    def hide_handles(self) -> None:
        self.handle_start.hide()
        self.handle_end.hide()

    def show(self) -> None:
        super().show()
        self.show_handles()

    def hide(self) -> None:
        super().hide()
        self.hide_handles()

    def set_movable(self, movable: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, movable)


class GraphicsEllipseItem(QGraphicsEllipseItem):
    def __init__(self,
                 rect: QRect,
                 pos: QPoint,
                 selectable: bool = False,
                 movable: bool = False,
                 accept_hover: bool = False):
        super().__init__(rect)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, selectable)
        self.set_movable(movable)
        self.setAcceptHoverEvents(accept_hover)

    def set_movable(self, movable: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, movable)


class GraphicsTextItem(QGraphicsTextItem):
    def __init__(self,
                 content: str,
                 pos: QPoint,
                 selectable: bool = False,
                 movable: bool = False,
                 accept_hover: bool = False):
        super().__init__(content)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, selectable)
        self.set_movable(movable)
        self.setAcceptHoverEvents(accept_hover)

    def set_movable(self, movable: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, movable)


class GraphicsView(SubObject, QGraphicsView):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 size: QSize):
        QGraphicsView.__init__(self, parent=obj.frame)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)
        self.margin = 0

        self.setScene(QGraphicsScene(QRect(QPoint(), size - QSize(self.margin, self.margin))))

    def set_scene_size(self, width: int, height: int, update_view_size: bool = False) -> None:
        self.setSceneRect(QRect(QPoint(0, 0), QSize(width, height)))
        if update_view_size:
            self.setFixedSize(width + self.margin, height + self.margin)


####################################################################################################
# Lineedit
####################################################################################################


class BaseLineedit(QLineEdit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 text: str,
                 readonly: bool = False,
                 align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
        super().__init__(parent=obj.frame)

        self.setText(text)
        self.setCursorPosition(0)
        self.setReadOnly(readonly)
        self.setAlignment(align)

    def set_plain_text(self, text: str) -> None:
        self.setText(text)

    def get_plain_text(self) -> str:
        return self.text()


class EmbeddedLineedit(EmbeddedObject, BaseLineedit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 text: str,
                 size: QSize = None,
                 readonly: bool = False,
                 align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
        BaseLineedit.__init__(self, obj=obj, text=text, readonly=readonly, align=align)
        EmbeddedObject.__init__(self, obj=obj, size=size)


class Lineedit(SubObject, BaseLineedit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 text: str,
                 size: QSize = None,
                 readonly: bool = False,
                 align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft):
        BaseLineedit.__init__(self, obj=obj, text=text, readonly=readonly, align=align)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)


####################################################################################################
# PlainTextEdit
####################################################################################################


class BasePlainTextEdit(QPlainTextEdit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 text: str,
                 readonly: bool = False):
        super().__init__(parent=obj.frame)

        self.setPlainText(text)
        self.setReadOnly(readonly)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.textChanged.connect(self.update_size)

    def set_plain_text(self, text: str) -> None:
        self.setPlainText(text)

    def get_plain_text(self) -> str:
        return self.document().toPlainText()

    def update_size(self) -> None:
        height = int(max(self.document().size().height(), 1) * QFontMetrics(self.font()).height() +
                     self.contentsMargins().top() + self.contentsMargins().bottom() +
                     self.document().rootFrame().frameFormat().margin() * 2)
        self.setFixedHeight(height)


class EmbeddedPlainTextEdit(EmbeddedObject, BasePlainTextEdit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 text: str,
                 size: QSize = None,
                 readonly: bool = False):
        BasePlainTextEdit.__init__(self, obj=obj, text=text, readonly=readonly)
        EmbeddedObject.__init__(self, obj=obj, size=size)


class PlainTextEdit(SubObject, BasePlainTextEdit):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 text: str,
                 size: QSize = None,
                 readonly: bool = False):
        BasePlainTextEdit.__init__(self, obj=obj, text=text, readonly=readonly)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)


####################################################################################################
# Checkbox
####################################################################################################


class BaseCheckbox(QCheckBox):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 state: Qt.CheckState):
        super().__init__(obj.frame)

        self.setCheckState(state)


class EmbeddedCheckbox(EmbeddedObject, BaseCheckbox):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 state: Qt.CheckState,
                 size: QSize = QSize(20, 20)):
        BaseCheckbox.__init__(self, obj=obj, state=state)
        EmbeddedObject.__init__(self, obj=obj, size=size)


class Checkbox(SubObject, BaseCheckbox):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 state: Qt.CheckState,
                 size: QSize = QSize(20, 20)):
        BaseCheckbox.__init__(self, obj=obj, state=state)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)


####################################################################################################
# Table
####################################################################################################


@unique
class TableCellType(Enum):
    LINEEDIT_READONLY = auto()
    LINEEDIT_EDITABLE = auto()
    PLAINTEXT_READONLY = auto()
    PLAINTEXT_EDITABLE = auto()
    IMAGE = auto()
    WIDGET = auto()


class TableCell:
    def __init__(self,
                 key: str,
                 value: Any,
                 _type: TableCellType,
                 size: QSize = None):
        self.key = key
        self.value = value
        self.type = _type
        self.size = size


class TableRow:
    def __init__(self,
                 data: Dict[str, TableCell] = None,
                 check: Qt.CheckState = Qt.CheckState.Unchecked):
        self.data = data or {}
        self.check = check


class BaseTable(QTableWidget):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 enable_checkbox: bool = True):
        super().__init__(obj.frame)

        self.enable_checkbox = enable_checkbox

        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)

        self.table_header: List[str] = []
        self.table_data: List[TableRow] = []

    def render_list(self, table_header: List[str], table_data: List[TableRow]) -> None:
        self.table_header = table_header
        self.table_data = table_data

        self.setColumnCount(len(table_header) + (1 if self.enable_checkbox else 0))
        self.setRowCount(len(table_data))
        self.setHorizontalHeaderLabels([''] + table_header if self.enable_checkbox else table_header)

        for row_idx, table_row in enumerate(table_data):
            if self.enable_checkbox:
                checkbox = EmbeddedCheckbox(obj=cast(Union[Table, EmbeddedTable], self),
                                            state=table_row.check,
                                            size=QSize(20, 20))
                checkbox.stateChanged.connect(lambda value, _table_row=table_row, _row_idx=row_idx:
                                              self.on_checkbox_change(_table_row, value, _row_idx))
                self.setCellWidget(row_idx, 0, checkbox)

            for table_cell in table_row.data.values():
                if table_cell.type == TableCellType.LINEEDIT_READONLY:
                    cell = EmbeddedLineedit(obj=cast(Union[Table, EmbeddedTable], self),
                                            text=table_cell.value,
                                            size=table_cell.size,
                                            readonly=True)

                elif table_cell.type == TableCellType.LINEEDIT_EDITABLE:
                    cell = EmbeddedLineedit(obj=cast(Union[Table, EmbeddedTable], self),
                                            text=table_cell.value,
                                            size=table_cell.size)
                    cell.textChanged.connect(lambda _table_cell=table_cell, editor=cell, _row_idx=row_idx:
                                             self.on_plain_text_edit_change(_table_cell, editor, _row_idx))

                elif table_cell.type == TableCellType.PLAINTEXT_READONLY:
                    cell = EmbeddedPlainTextEdit(obj=cast(Union[Table, EmbeddedTable], self),
                                                 text=table_cell.value,
                                                 size=table_cell.size,
                                                 readonly=True)

                elif table_cell.type == TableCellType.PLAINTEXT_EDITABLE:
                    cell = EmbeddedPlainTextEdit(obj=cast(Union[Table, EmbeddedTable], self),
                                                 text=table_cell.value,
                                                 size=table_cell.size)
                    cell.textChanged.connect(lambda _table_cell=table_cell, editor=cell, _row_idx=row_idx:
                                             self.on_plain_text_edit_change(_table_cell, editor, _row_idx))

                else:
                    cell = None

                if cell:
                    self.setCellWidget(row_idx, table_header.index(table_cell.key) + (1 if self.enable_checkbox else 0), cell)

        self.update_height()

    @staticmethod
    def on_checkbox_change(table_row: TableRow, state, row_idx: int) -> None:
        table_row.check = Qt.CheckState(state)

    def on_plain_text_edit_change(self, table_cell: TableCell, editor: EmbeddedPlainTextEdit, row_idx: int) -> None:
        table_cell.value = editor.get_plain_text()
        self.update_row_height(row_idx)

    def update_row_height(self, row_idx: int) -> None:
        offset = 1 if self.enable_checkbox else 0
        height = 0

        for col_idx in range(offset, len(self.table_header) + offset):
            widget = self.cellWidget(row_idx, col_idx)
            if widget:
                if hasattr(widget, 'update_size'):
                    widget.update_size()
                height = max(height, widget.size().height())

        self.setRowHeight(row_idx, height)

    def update_height(self) -> None:
        for row_idx in range(len(self.table_data)):
            self.update_row_height(row_idx)

    def update_col_width(self, col_idx: int) -> None:
        width = 20

        for row_idx in range(len(self.table_data)):
            widget = self.cellWidget(row_idx, col_idx)
            if widget:
                if hasattr(widget, 'update_size'):
                    widget.update_size()
                width = max(width, widget.size().width())

        self.setColumnWidth(col_idx, width)

    def update_width(self) -> None:
        for col_idx in range(len(self.table_header) + (1 if self.enable_checkbox else 0)):
            self.update_col_width(col_idx)


class EmbeddedTable(EmbeddedObject, BaseTable):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 size: QSize = None,
                 enable_checkbox: bool = True):
        BaseTable.__init__(self, obj=obj, enable_checkbox=enable_checkbox)
        EmbeddedObject.__init__(self, obj=obj, size=size)


class Table(SubObject, BaseTable):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 size: QSize = None,
                 enable_checkbox: bool = True):
        BaseTable.__init__(self, obj=obj, enable_checkbox=enable_checkbox)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)


####################################################################################################
# Function
####################################################################################################


@unique
class FuncArgParseType(Enum):
    none = auto()
    click = auto()
    dclick = auto()


class FuncArg:
    def __init__(self,
                 key: str,
                 value: str = None,
                 check: bool = False,
                 is_key_output: bool = True,
                 comment: str = None,
                 parse_key: Callable = None,
                 parse_value: Callable = None,
                 parse_type: str = FuncArgParseType.none,
                 readonly_value: bool = False):
        self.key = key
        self.value = value
        self.check = Qt.CheckState.Checked if check else Qt.CheckState.Unchecked
        self.is_key_output = is_key_output
        self.comment = comment
        self.parse_key = parse_key or (lambda x: ' {0}'.format(x))
        self.parse_value = parse_value or (lambda x: ' {0}'.format(x))
        self.parse_type = parse_type
        self.readonly_value = readonly_value

    def parse(self) -> str:
        result = ''
        if self.check == Qt.CheckState.Checked:
            if self.is_key_output:
                result += self.parse_key(self.key)
            if self.value:
                result += self.parse_value(self.value)
        return result


class Func:
    def __init__(self,
                 name: str,
                 click_func: Callable = (lambda x: None),
                 dclick_func: Callable = (lambda x: None),
                 args: List[FuncArg] = None,
                 args_parser: Callable = (lambda x: x),
                 parent=None,
                 children=None):
        self.name = name
        self.click_func = click_func
        self.dclick_func = dclick_func
        self.args = args or []  # TODO: list or dict?
        self.args_parser = args_parser
        self.parent: Func = parent
        self.children: List[Func] = children or []
        self.is_leaf = False if self.children else True

    def click(self) -> None:
        args = [arg for arg in self.args if arg.parse_type == FuncArgParseType.click]
        self.click_func(self.args_parser(args))

    def double_click(self) -> None:
        args = [arg for arg in self.args if arg.parse_type == FuncArgParseType.dclick]
        self.dclick_func(self.args_parser(args))


class FuncArgsTable(Table):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 size: QSize = None):
        Table.__init__(self, obj=obj, pos=pos, size=size)

        self.func = None

        self.setColumnCount(3)
        self.horizontalHeader().setStretchLastSection(True)

        self.table_data: List[TableRow] = []

        self.table_header: List[str] = ['key', 'value']

    def render_func(self, func: Func) -> None:
        self.func = func
        self.setRowCount(len(func.args))

        self.clear()
        self.table_data.clear()

        for row_idx, arg in enumerate(func.args):
            table_row = TableRow(check=arg.check, data={
                'key': TableCell(
                    key='key',
                    value=arg.key,
                    _type=TableCellType.PLAINTEXT_READONLY,
                    size=QSize(100, 0)),
                'value': TableCell(
                    key='value',
                    value=arg.value,
                    _type=TableCellType.PLAINTEXT_READONLY if arg.readonly_value else TableCellType.PLAINTEXT_EDITABLE,
                    size=QSize(150, 0))
            })
            self.table_data.append(table_row)

        self.render_list(self.table_header, self.table_data)

    def on_checkbox_change(self, table_row: TableRow, state, row_idx) -> None:
        super().on_checkbox_change(table_row, state, row_idx)
        self.func.args[row_idx].check = Qt.CheckState(state)

    def on_plain_text_edit_change(self, table_cell: TableCell, editor: EmbeddedPlainTextEdit, row_idx: int) -> None:
        super().on_plain_text_edit_change(table_cell, editor, row_idx)
        self.func.args[row_idx].value = editor.get_plain_text()


class FuncTree(SubObject, QTreeWidget):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 func_list: List[Func]):
        QTreeWidget.__init__(self, parent=obj.frame)
        SubObject.__init__(self, obj=obj, pos=pos, size=QSize(300, 300))

        self.is_show = False

        self.clicked.connect(self.on_mouse_click)
        self.doubleClicked.connect(self.on_mouse_double_click)

        self.func_args_table = self.parent_object.add_object(
            FuncArgsTable(obj=self, pos=self.global_pos + QPoint(0, self.height()), size=QSize(300, 300)))
        self.hide_func_args_table()

        self.map_func: Dict[QTreeWidgetItem, Func] = {}
        self.last_item = None

        self.setColumnCount(1)
        self.setHeaderLabels(['Function'])

        def build_tree(tree: List[Func], parent, level) -> None:
            for func in tree:
                node = QTreeWidgetItem([func.name])

                if level == 0:
                    parent.addTopLevelItem(node)
                else:
                    parent.addChild(node)

                self.map_func.update({node: func})

                if not func.is_leaf:
                    build_tree(func.children, node, level + 1)

        build_tree(func_list, self, 0)
        # self.on_mouse_click()

    def on_mouse_click(self) -> None:
        item = self.currentItem()
        if item in self.map_func:
            self.map_func[item].click()

        if item != self.last_item:
            func = self.map_func[item]
            if func.args:
                self.show_func_args_table()
                self.func_args_table.render_func(func)
            else:
                self.hide_func_args_table()
            self.last_item = item

    def on_mouse_double_click(self) -> None:
        item = self.currentItem()
        if item in self.map_func:
            self.map_func[item].double_click()

    def deleteLater(self) -> None:  # noqa  # TODO
        # self.obj.widget_object_manager.delete_from_render_data(self.func_args_table)
        super().deleteLater()

    def show_func_args_table(self):
        self.func_args_table.show()

    def hide_func_args_table(self):
        self.func_args_table.hide()


####################################################################################################
# Pushbutton
####################################################################################################


class PushButton(SubObject, QPushButton):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 content: Union[str, QImage, QPixmap],
                 size: QSize = None,
                 is_default_select: bool = False,
                 is_changeable: bool = True,
                 func_select: Func = Func(''),
                 func_unselect: Func = Func('')):
        QPushButton.__init__(self, parent=obj.frame)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)

        self.content = content

        self.is_select = False
        self.is_default_select = is_default_select
        self.is_changeable = is_changeable

        self.func_select = func_select
        self.func_unselect = func_unselect

        self.press_start_pos = QPoint()
        self.last_global_pos = copy.deepcopy(self.global_pos)
        self.is_dragging = False
        self.is_clicking = False
        self.start_time = common.Time().timestamp

        self.move_and_show()

        self.reset()

    def reset(self) -> None:
        if self.is_default_select:
            self.select(force=True)
        else:
            self.unselect(force=True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_start_pos = event.globalPos()
            self.last_global_pos = copy.deepcopy(self.global_pos)
            self.is_dragging = True
            self.is_clicking = True
            self.is_self_moving.set(True)
            self.start_time = common.Time().timestamp

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.is_dragging:
            pos_diff = event.globalPos() - self.press_start_pos
            self.update_global_pos(self.last_global_pos + pos_diff)
            self.move_and_show()

            if pos_diff.manhattanLength() > Config.Object.SubObject.Click().cursor_move_distance_tolerance:
                self.is_clicking = False

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        time_diff = common.Time().timestamp - self.start_time
        if time_diff <= Config.Object.SubObject.Click().cursor_press_time_tolerance and self.is_clicking:
            self.click()

        self.is_dragging = False
        self.is_clicking = False
        self.is_self_moving.set(False)

        super().mouseReleaseEvent(event)

    def click(self) -> None:
        if self.is_select:
            self.unselect()
        else:
            self.select()

    def pseudo_click(self) -> None:
        if self.is_changeable:
            if self.is_select:
                self.set_style_sheet(False)
            else:
                self.set_style_sheet(True)

    def reset_pseudo_click(self) -> None:
        if self.is_changeable:
            self.set_style_sheet(self.is_select)

    def select(self, force=False) -> None:
        if self.is_changeable or force:
            self.is_select = True
            self.set_style_sheet(self.is_select)

        self.func_select.click()

    def unselect(self, force=False) -> None:
        if self.is_changeable or force:
            self.is_select = False
            self.set_style_sheet(self.is_select)

        self.func_unselect.click()

    def set_style_sheet(self, is_select: bool) -> None:
        pass


class TextMenu(SubObjectMenu):
    def __init__(self,
                 text: 'Text'):
        super().__init__(text)

        self.text = text

        self.addAction(Action(
            menu=self,
            text='Copy Text',
            func=Func('Copy Text', click_func=lambda: self.text.widget_clipboard.set_text(self.text.content))
        ))


class Text(PushButton):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 text: str,
                 size: QSize = None,
                 is_default_select: bool = False,
                 is_changeable: bool = True,
                 func_select: Func = Func(''),
                 func_unselect: Func = Func('')):
        super().__init__(obj=obj,
                         pos=pos,
                         size=size,
                         content=text,
                         is_default_select=is_default_select,
                         is_changeable=is_changeable,
                         func_select=func_select,
                         func_unselect=func_unselect)

        self.setText(text)
        if size:
            self.resize(size)
        else:
            self.resize(self.sizeHint())
        self.move_and_show()

        self.widget_clipboard: Any = self.frame.load_widget(self, 'widget_clipboard')
        self.menu = TextMenu(self)

        self.reset()

    def set_style_sheet(self, is_select: bool) -> None:
        if is_select:
            self.setStyleSheet(Config.Object.Text().BgColor().selected)
        else:
            self.setStyleSheet(Config.Object.Text().BgColor().unselected)
        self.show()


class ImageMenu(SubObjectMenu):
    def __init__(self,
                 image: 'Image'):
        super().__init__(image)

        self.image = image

        self.addAction(Action(
            menu=self,
            text='Copy Image',
            func=Func('Copy Image', click_func=lambda: self.image.widget_clipboard.set_image(self.image.content))
        ))


class Image(PushButton):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: Union[QPoint, RelativePos],
                 image: QPixmap,
                 size: QSize = None,
                 is_default_select: bool = False,
                 is_changeable: bool = True,
                 func_select: Func = Func(''),
                 func_unselect: Func = Func('')):
        super().__init__(obj=obj,
                         pos=pos,
                         size=size,
                         content=image,
                         is_default_select=is_default_select,
                         is_changeable=is_changeable,
                         func_select=func_select,
                         func_unselect=func_unselect)

        self.widget_clipboard: Any = self.frame.load_widget(self, 'widget_clipboard')
        self.scaled_image = image

        self.menu = ImageMenu(self)
        self.is_resizing = common.ToggleBool()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.drawPixmap(self.scaled_image.rect(), self.scaled_image)
        self.resize(self.scaled_image.size())

    def resize_bounding_rect(self, size: QSize) -> None:
        with self.is_resizing:
            self.scaled_image = self.content.scaled(
                size, aspectMode=Qt.AspectRatioMode.KeepAspectRatio, mode=Qt.TransformationMode.SmoothTransformation)


####################################################################################################
# Tab
####################################################################################################


class Page:
    def __init__(self,
                 title: str = '',
                 frontend=None,
                 func_list: List = None,
                 delete_later: Callable = None):
        self.title = title
        self.frontend = frontend
        self.func_list = func_list or []
        self.deleteLater = delete_later or (lambda: None)


class Tab(SubObject, QTabWidget):
    def __init__(self,
                 obj: Union[SubObject, EmbeddedObject, Object],
                 pos: QPoint,
                 size: QSize):
        QTabWidget.__init__(self, parent=obj.frame)
        SubObject.__init__(self, obj=obj, pos=pos, size=size)

        self.setTabShape(QTabWidget.TabShape.Triangular)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(lambda page_idx: self.delete_page(page_idx))
        self.currentChanged.connect(lambda page_idx: self.on_page_change(page_idx))

        class TypingPageList(TypedDict):
            page: Page
            func_tree: FuncTree

        self.page_list: Dict[int, TypingPageList] = {}
        self.active_page_idx = 0

    def on_page_change(self, page_idx: int) -> None:
        if self.active_page_idx in self.page_list:
            self.hide_page_func(self.active_page_idx)

        new_page_list = {self.indexOf(page['page'].frontend): page for page in list(self.page_list.values())}
        self.page_list = new_page_list

        if self.page_list:
            self.show_page_func(page_idx)
        self.active_page_idx = page_idx

    def add_page(self, page: Page) -> int:
        page_idx = len(self.page_list)
        if page_idx in self.page_list:
            self.frame.logger.error('page_idx = {0}'.format(page_idx))
            return -1
        else:
            if page.frontend is None:
                self.frame.logger.error('frontend is required in the page')
                return -1

            self.addTab(page.frontend, page.title)

            pos_x, pos_y = self.global_pos.x() + self.width(), self.global_pos.y()
            func_tree = self.add_object(FuncTree(self, QPoint(pos_x, pos_y), page.func_list))

            self.page_list.update({page_idx: {
                'page': page,
                'func_tree': func_tree
            }})

            return page_idx

    def delete_page(self, page_idx: int, close_on_empty: bool = True) -> None:
        if page_idx in self.page_list:
            self.page_list[page_idx]['page'].deleteLater()
            self.remove_object(self.page_list[page_idx]['func_tree'])
            self.page_list.pop(page_idx)
            self.removeTab(page_idx)

            if close_on_empty and not self.page_list:
                self.close()
        else:
            self.frame.logger.error('page_idx = {0}'.format(page_idx))

    def delete_all_pages(self) -> None:
        for page_idx in list(self.page_list.keys()):
            self.delete_page(page_idx, close_on_empty=False)

    def show_page_func(self, page_idx: int) -> None:
        if page_idx in self.page_list:
            func_tree = self.page_list[page_idx]['func_tree']
            func_tree.show()
            func_tree.show_func_args_table()
        else:
            self.frame.logger.error('page_idx = {0}'.format(page_idx))

    def hide_page_func(self, page_idx: int) -> None:
        if page_idx in self.page_list:
            func_tree = self.page_list[page_idx]['func_tree']
            func_tree.hide()
            func_tree.hide_func_args_table()
        else:
            self.frame.logger.error('page_idx = {0}'.format(page_idx))


####################################################################################################
# WidgetBase
####################################################################################################


class WidgetBase(QWidget):
    def __init__(self,
                 frame: Frame):
        super().__init__(frame)

        self.frame = frame
        self.is_auto_start = False
        self.work_status = 'stop'

    def reset(self) -> None:
        pass

    def enable_widget(self) -> None:
        self.work_status = 'working'

    def disable_widget(self) -> None:
        self.work_status = 'stop'

    def auto_start(self) -> None:
        if self.is_auto_start:
            self.enable_widget()
