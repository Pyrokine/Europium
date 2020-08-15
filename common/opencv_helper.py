import cv2
import numpy as np


def bgr_to_hsv(image: np.array) -> np.array:
    return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)


def hsv_to_bgr(image: np.array) -> np.array:
    return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)


def change_rgb_image_brightness(image: np.array, value):
    image_hsv = bgr_to_hsv(image)
    image_hsv[:, :, 2] = cv2.add(image_hsv[:, :, 2], value)
    return hsv_to_bgr(image_hsv)
