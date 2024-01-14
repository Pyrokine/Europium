from typing import Union
from config import Config

import numpy as np
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QImage, QPixmap


def qimage_to_qpixmap(image: QImage) -> QPixmap:
    return QPixmap().fromImage(image)


def qpixmap_to_qimage(image: QPixmap) -> QImage:
    return image.toImage()


def qimage_to_numpy_bgr(image: QImage) -> np.array:
    return np.array(image.bits(), dtype=np.uint8).reshape(image.height(), image.width(), 4)[:, :, :3]


def qpixmap_to_numpy_bgr(image: QPixmap) -> np.array:
    return qimage_to_numpy_bgr(image.toImage())


def numpy_bgr_to_qpimage(image: np.array) -> QImage:
    if image.ndim == 3:
        return QImage(image.tobytes(), image.shape[1], image.shape[0], image.shape[1] * 3, QImage.Format.Format_BGR888)
    else:
        print('not support')
        return QImage()


def numpy_bgr_to_qpixmap(image: np.array) -> QPixmap:
    return QPixmap.fromImage(numpy_bgr_to_qpimage(image))


def resize_image(image: Union[QImage, QPixmap],
                 size: QSize,
                 aspect_ratio_mode: Qt.AspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio,
                 transformation_mode: Qt.TransformationMode = Qt.TransformationMode.SmoothTransformation) -> Union[QImage, QPixmap]:
    return image.scaled(size, aspectMode=aspect_ratio_mode, mode=transformation_mode)


def create_thumbnail(image: Union[QImage, QPixmap]) -> Union[QImage, QPixmap]:
    return resize_image(image, Config.Converter().thumbnail_size)


def file_url_to_file_path(string: str) -> str:
    url = QUrl(string)
    return url.toLocalFile()
