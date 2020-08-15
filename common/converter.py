from PySide6.QtGui import QImage, QPixmap
import numpy as np
import cv2


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
