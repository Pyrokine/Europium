from PySide6.QtCore import QPoint, QFileInfo
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import QFileIconProvider

from common import common, widget_base, converter


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_drag_and_drop')
        self.is_auto_start = True

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()
        self.frame.signalDragEnter.connect(self.on_drag_enter)
        self.frame.signalDragMove.connect(self.on_drag_move)
        self.frame.signalDragLeave.connect(self.on_drag_leave)
        self.frame.signalDrop.connect(self.on_drop)

    def disable_widget(self) -> None:
        super().disable_widget()
        self.frame.signalDragEnter.disconnect(self.on_drag_enter)
        self.frame.signalDragMove.disconnect(self.on_drag_move)
        self.frame.signalDragLeave.disconnect(self.on_drag_leave)

    @staticmethod
    def on_drag_enter(event: QDragEnterEvent) -> None:
        event.accept()

    @staticmethod
    def on_drag_move(event: QDragMoveEvent) -> None:
        event.accept()

    @staticmethod
    def on_drag_leave(event: QDragLeaveEvent) -> None:
        event.accept()

    def on_drop(self, event: QDropEvent) -> None:
        event.accept()
        mime = event.mimeData()

        obj: widget_base.Object = self.frame.widget_object_manager.generate_object()
        obj.mime = common.copy_mime_data(mime, customized=True)
        pos_x, pos_y = obj.global_pos.x(), obj.global_pos.y()

        file_path = obj.mime.text()

        if common.is_file_url(file_path):
            file_path = converter.file_url_to_file_path(file_path)
            file_info = QFileInfo(file_path)
            file_icon_provider = QFileIconProvider()
            file_icon = file_icon_provider.icon(file_info)
        else:
            file_icon = None

        text: widget_base.Text = obj.add_object(widget_base.Text(obj=obj, pos=QPoint(pos_x, pos_y), text=file_path, icon=file_icon))
        pass
