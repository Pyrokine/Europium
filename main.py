import sys

from PySide6.QtWidgets import QApplication
from common.widget_base import Frame


if __name__ == '__main__':
    app = QApplication([])
    demo = Frame(is_import_module=True)
    demo.show()
    sys.exit(app.exec())
