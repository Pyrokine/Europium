from typing import List, Callable, Optional, Dict

from PySide6.QtGui import QShortcut, QKeySequence

from common import common, widget_base


class Shortcut:
    def __init__(self,
                 widget: widget_base.WidgetBase,
                 shortcut_name: str,
                 shortcut_key: List[str],
                 callback: Callable):
        self.widget = widget
        self.shortcut_name = shortcut_name
        self.shortcut_key = '+'.join(shortcut_key)
        self.callback = callback

        self.shortcut = QShortcut(QKeySequence(self.shortcut_key), widget.frame)


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)
        self.setObjectName('widget_shortcut')
        self.is_auto_start = True

        self.map_shortcut: Dict[str, Shortcut] = {}

        self.reset()

    def enable_widget(self):
        super().enable_widget()
        # TODO

    def disable_widget(self):
        super().disable_widget()

    def verify_shortcut(self, shortcut) -> Optional[Shortcut]:
        if shortcut.shortcut_key not in self.map_shortcut:
            self.frame.logger.error('[{0}] does not exist'.format(shortcut.shortcut_name))
            return None

        if shortcut != self.map_shortcut[shortcut.shortcut_key]:
            self.frame.logger.error('[{0}] is conflict with [{1}]'.format(
                shortcut.shortcut_name, self.map_shortcut[shortcut.shortcut_key].shortcut_name))
            return None

        return shortcut

    def add_shortcut(self, shortcut: Shortcut, enable: bool = True) -> bool:
        if shortcut.shortcut_key not in self.map_shortcut:
            self.map_shortcut.update({shortcut.shortcut_key: shortcut})
            if enable:
                self.enable_shortcut(shortcut)
            return True
        else:
            self.frame.logger.error('[{0}] is conflict with [{1}]'.format(
                shortcut.shortcut_name, self.map_shortcut[shortcut.shortcut_key].shortcut_name))
            return False

    def remove_shortcut(self, shortcut: Shortcut):
        if not self.verify_shortcut(shortcut):
            return False

        self.map_shortcut.pop(shortcut.shortcut_key)
        return True

    def enable_shortcut(self, shortcut: Shortcut) -> bool:
        if not self.verify_shortcut(shortcut):
            return False

        shortcut.shortcut.activated.connect(shortcut.callback)
        return True

    def disable_shortcut(self, shortcut: Shortcut) -> bool:
        if not self.verify_shortcut(shortcut):
            return False

        shortcut.shortcut.activated.disconnect(shortcut.callback)
        return True
