import datetime
from pathlib import Path
import os


class Time:
    def __init__(self, offset_day=0, offset_hour=8, offset_minute=0, offset_second=0, offset_millisecond=0):
        self.time_array = datetime.datetime.utcnow() + datetime.timedelta(
            days=offset_day,
            hours=offset_hour,
            minutes=offset_minute,
            seconds=offset_second,
            milliseconds=offset_millisecond
        )
        self.timestamp = self.time_array.timestamp()
        self.date_and_time = self.time_array.strftime('%Y-%m-%d %H:%M:%S')
        self.date_and_time2 = self.time_array.strftime('%Y-%m-%d_%H-%M-%S')
        self.date = self.time_array.strftime('%Y-%m-%d')
        self.time = self.time_array.strftime('%H:%M:%S')
        self.year = self.time_array.year
        self.month = self.time_array.month
        self.day = self.time_array.day
        self.hour = self.time_array.hour
        self.minute = self.time_array.minute
        self.second = self.time_array.second


class ToggleBool:
    def __init__(self, val: bool = False):
        self.__val = val

    def __bool__(self):
        return self.__val

    def __enter__(self):
        self.__val = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__val = False

    def set(self, val: bool):
        self.__val = val


def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def is_rec_overlapped(a_left, a_right, a_top, a_bottom, b_left, b_right, b_top, b_bottom) -> bool:
    if max(a_left, b_left) <= min(a_right, b_right) and max(a_top, b_top) <= min(a_bottom, b_bottom):
        return True
    else:
        return False


def is_rec_a_contain_b(a_left, a_right, a_top, a_bottom, b_left, b_right, b_top, b_bottom) -> bool:
    if a_left <= b_left and a_right >= b_right and a_top <= b_top and a_bottom >= b_bottom:
        return True
    else:
        return False


def is_point_a_in_rec_b(a_x, a_y, b_left, b_right, b_top, b_bottom) -> bool:
    if b_left <= a_x <= b_right and b_top <= a_y <= b_bottom:
        return True
    else:
        return False


def join_path(*args):
    return Path(os.path.join(*args)).as_posix()
