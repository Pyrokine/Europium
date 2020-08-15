import os
from collections import deque

from common import common, widget_base
from widgets import widget_shortcut


class FileManager:
    def __init__(self, obj: widget_base.Object):
        self.obj = obj
        self.func_list = {}

        self.process_list = deque()
        func_list = [self.generate_dir_tree(os.path.abspath('.'))]
        self.func_tree = obj.add_object(widget_base.FuncTree(obj, self.obj.global_pos, func_list))
        self.func_tree.show()

    def generate_dir_tree(self, abs_path) -> widget_base.Func:
        root = widget_base.Func(name=os.path.basename(abs_path), args=[widget_base.FuncArg('abs_path', abs_path)])
        self.process_list.append([root, abs_path])

        while self.process_list:
            self.process(*self.process_list[0])
            self.process_list.popleft()

        return root

    def process(self, father: widget_base.Func, abs_path) -> None:
        if os.path.isdir(abs_path):
            father.is_leaf = False
            for rel_path in sorted(os.listdir(abs_path)):
                func = widget_base.Func(name=rel_path, args=[widget_base.FuncArg('abs_path', common.join_path(abs_path, rel_path))])
                father.children.append(func)
                self.process_list.append([func, common.join_path(abs_path, rel_path)])
        else:
            father.is_leaf = True


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_file_manager')
        self.is_auto_start = True

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='generate file manager',
                                                 shortcut_key=['Ctrl', 'M'],
                                                 callback=self.generate_file_manager)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def generate_file_manager(self):
        obj = self.frame.widget_object_manager.generate_object()
        FileManager(obj)
