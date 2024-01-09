from common import widget_base, pipeline_base, common, converter
from widgets import widget_clipboard, widget_render

from PySide6.QtCore import QMimeData


class Pipeline(pipeline_base.PipelineBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('pipeline_clipboard_render')
        self.is_auto_start = True

        self.widget_clipboard: widget_clipboard.Widget = widget_clipboard.Widget(frame)
        self.widget_render: widget_render.Widget = widget_render.Widget(frame)

        self.reset()

    def enable_widget(self):
        self.widget_clipboard.signalClipboardPaste.connect(self.clipboard_render)

    def disable_widget(self):
        self.widget_clipboard.signalClipboardPaste.disconnect(self.clipboard_render)

    def clipboard_render(self, mime: QMimeData):
        mime = self.widget_clipboard.mime_generate_render_list(mime)

        for idx, render_data in enumerate(mime.render_list):
            if render_data.render_type == widget_base.RenderType.RENDER_TYPE_PLAIN_TEXT and common.is_file_url(render_data.content):
                mime.render_list[idx].content = converter.string_to_file_path(render_data.content)
            elif render_data.render_type == widget_base.RenderType.RENDER_TYPE_QIMAGE:
                mime.render_list[idx].content = converter.create_thumbnail(render_data.content)

        self.widget_render.render_to_frame(mime)
