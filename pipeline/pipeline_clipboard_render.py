from common import widget_base, pipeline_base
from widgets import widget_clipboard, widget_parser, widget_qq_helper, widget_render


class Pipeline(pipeline_base.PipelineBase):
    def __init__(self, frame: widget_base.Frame):
        super().__init__(frame)

        self.setObjectName('pipeline_clipboard_render')
        self.is_auto_start = True

        self.widget_clipboard: widget_clipboard.Widget = widget_clipboard.Widget(frame)
        self.widget_parser: widget_parser.Widget = widget_parser.Widget(frame)
        self.widget_qq_helper: widget_qq_helper.Widget = widget_qq_helper.Widget(frame)
        self.widget_render: widget_render.Widget = widget_render.Widget(frame)

        self.reset()

    def enable_widget(self):
        self.widget_clipboard.signalClipboardPaste.connect(self.clipboard_render)

    def disable_widget(self):
        self.widget_clipboard.signalClipboardPaste.disconnect(self.clipboard_render)

    def clipboard_render(self, idx: int):
        mime = self.frame.mime_data[idx]
        text_image = self.widget_parser.extract_text_image_from_mime_data(mime['mime'])
        text_image = self.widget_qq_helper.extract_qq_image_from_text_image(text_image)
        self.widget_render.render_text_image(text_image)
