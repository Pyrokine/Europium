from PySide6.QtWidgets import QWidget

from common import widget_base


class PipelineBase(QWidget):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(None)

        self.frame = frame
        self.is_auto_start = True

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
