from PySide6.QtCore import QSize


class Config:
    class Main:
        def __init__(self):
            self.background_color = '#F0F0F0'

    class Object:
        class SubObject:
            class Click:
                def __init__(self):
                    self.cursor_move_distance_tolerance = 3  # pixel
                    self.cursor_press_time_tolerance = 300  # millisecond

        class Text:
            class BgColor:
                def __init__(self):
                    self.selected = 'background-color: rgb(255, 255, 255); border-style: none;'
                    self.unselected = 'background-color: rgb(240, 240, 240); border-style: none;'

        class Image:
            class BgColor:
                def __init__(self):
                    self.selected = 'background-color: rgb(255, 255, 255); border: 1px;'
                    self.unselected = 'background-color: rgb(240, 240, 240); border-style: none;'

    class Git:
        class CSS:
            def __init__(self):
                self.node_hollow_rad = 8
                self.node_solid_rad = 4
                self.node_interval = 25
                self.arc_rad = 8

    class SSH:
        class CSS:
            def __init__(self):
                self.line_height = 30

    class Converter:
        def __init__(self):
            self.thumbnail_size = QSize(300, 200)
