from collections import deque
from typing import Union

import pandas as pd
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget

from common import common, widget_base
from widgets import widget_shortcut


class ObjectManager:
    def __init__(self, frame: widget_base.Frame, obj: widget_base.Object):
        self.frame = frame
        self.obj = obj
        self.func_list = {}

        self.process_list = deque()
        func_list = [self.generate_object_tree()]
        self.func_tree = obj.add_object(widget_base.FuncTree(obj, self.obj.global_pos, func_list))
        self.func_tree.show()

    def generate_object_tree(self) -> widget_base.Func:
        root = widget_base.Func(name=self.frame.objectName())
        self.process_list.append([root, self.frame])

        while self.process_list:
            self.process(*self.process_list[0])
            self.process_list.popleft()

        return root

    def process(self, father: widget_base.Func, obj: Union[widget_base.SubObject, widget_base.EmbeddedObject, widget_base.Object]) -> None:
        if obj.children_objects:
            father.is_leaf = False
            for children_object in obj.children_objects:
                func = widget_base.Func(name=children_object.objectName())  # type:ignore
                father.children.append(func)
                self.process_list.append([func, children_object])
        else:
            father.is_leaf = True


@common.singleton
class Widget(widget_base.WidgetBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('widget_object_manager')
        self.is_auto_start = True

        self.frame.df_obj_pos = pd.DataFrame(columns=['idx', 'left', 'right', 'top', 'bottom'])

        self.widget_shortcut: widget_shortcut.Widget = widget_shortcut.Widget(frame)
        self.shortcut = widget_shortcut.Shortcut(widget=self,
                                                 shortcut_name='open object manager',
                                                 shortcut_key=['Ctrl', 'O'],
                                                 callback=self.render_tree)
        self.widget_shortcut.add_shortcut(self.shortcut)

        self.reset()

    def enable_widget(self) -> None:
        super().enable_widget()

    def disable_widget(self) -> None:
        super().disable_widget()

    def generate_object(self, frame: QWidget = None, pos: QPoint = None) -> widget_base.Object:
        if pos is None:
            pos = self.frame.get_cursor_global_pos()

        obj = widget_base.Object(frame or self.frame, pos, self.frame.render_idx)
        obj.frame.add_object(obj)

        return obj

    def add_to_render_data(self, obj) -> None:
        obj.render_idx = self.frame.render_idx

        self.frame.render_data.update({
            self.frame.render_idx: obj
        })

        # TODO: indispensable?
        self.frame.df_obj_pos.loc[len(self.frame.df_obj_pos)] = [  # type:ignore
            self.frame.render_idx,
            self.frame.render_data[self.frame.render_idx].global_pos_left,
            self.frame.render_data[self.frame.render_idx].global_pos_right,
            self.frame.render_data[self.frame.render_idx].global_pos_top,
            self.frame.render_data[self.frame.render_idx].global_pos_bottom
        ]

        self.frame.render_idx += 1

    def remove_from_render_data(self, obj) -> None:
        self.frame.render_data.pop(obj.render_idx)
        self.frame.df_obj_pos.drop(  # type:ignore
            index=self.frame.df_obj_pos[self.frame.df_obj_pos.idx == obj.render_idx].index.tolist(), inplace=True)  # type:ignore
        obj.deleteLater()

    def render_tree(self) -> None:
        obj = self.generate_object()
        ObjectManager(self.frame, obj)

    def get_grandfather_object(self,
                               obj: Union[widget_base.SubObject, widget_base.EmbeddedObject, widget_base.Object]) -> widget_base.Object:
        if isinstance(obj, widget_base.Object):
            return obj
        elif obj.parent_object:
            return self.get_grandfather_object(obj.parent_object)
        else:
            self.frame.logger.error('Cannot get grandfather object')
