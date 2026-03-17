import time

import numpy
from maa.context import Context, RecognitionDetail

from agent.logger import logger


def mount_vehicle(context: Context, mount_type: int = 0) -> bool:
    """
    如果识别到上/下载具按钮就上/下载具 | 其实如果不想识别直接按下 G 就行

    Args:
        context: 控制器上下文
        mount_type: 类型：0下载具，1上载具

    Returns: 是否成功

    """
    # 首次识别
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    entry = "图片识别上载具图标" if mount_type else "图片识别下载具图标"
    detail: RecognitionDetail | None = context.run_recognition(entry, img)  # TODO 上下载具图标绿幕切片
    if detail and detail.hit:
        context.tasker.controller.post_click(0, 0).wait()  # TODO 点击上下载具
        return True
    # 第一次未识别到：可能是在战斗技能页面 | 点击按钮切换页面
    time.sleep(1)
    context.tasker.controller.post_click(0, 0).wait()  # TODO 点击切换页面
    # 再次识别
    time.sleep(1)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    detail: RecognitionDetail | None = context.run_recognition(entry, img)  # TODO 上下载具图标绿幕切片
    if detail and detail.hit:
        context.tasker.controller.post_click(0, 0).wait()  # TODO 点击上下载具
        return True
    # 确实没识别到
    logger.error("未识别到上/下载具的图标")
    return False


def auto_attach(context: Context, attack_type: int = 0) -> bool:
    """
    如果识别到开/关自动战斗按钮就开/关自动战斗 | 其实如果不想识别直接按下 H 就行

    Args:
        context: 控制器上下文
        attack_type: 类型：0关自动战斗，1开自动战斗

    Returns: 是否成功

    """
    # 首次识别
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    entry = "图片识别开自动战斗" if attack_type else "图片识别关自动战斗"
    detail: RecognitionDetail | None = context.run_recognition(entry, img)  # TODO 开关自动战斗图标绿幕切片
    if detail and detail.hit:
        context.tasker.controller.post_click(0, 0).wait()  # TODO 点击开关自动战斗
        return True
    # 第一次未识别到：可能是在战斗技能页面 | 点击按钮切换页面
    time.sleep(1)
    context.tasker.controller.post_click(0, 0).wait()  # TODO 点击切换页面
    # 再次识别
    time.sleep(1)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    detail: RecognitionDetail | None = context.run_recognition(entry, img)  # TODO 开关自动战斗图标绿幕切片
    if detail and detail.hit:
        context.tasker.controller.post_click(0, 0).wait()  # TODO 点击开关自动战斗
        return True
    # 确实没识别到
    logger.error("未识别到开/关自动战斗的图标")
    return False


def attach_rotate_view(context: Context, rotate_times: int = 0, interval: int = 1) -> bool:
    """
    战斗视角旋转

    Args:
        context: 控制器上下文
        rotate_times: 旋转次数，rotate_times >= 0，0为不限次数
        interval: 每次旋转的间隔，interval >= 1

    Returns: 是否成功

    """
    # 校验参数
    rotate_times = 0 if rotate_times < 0 else rotate_times
    interval = 1 if interval < 1 else interval

    # 旋转视角
    if rotate_times == 0:
        # 不限次数的情况下进行持续旋转
        while True:
            # 滑动时间：1，触控点：1 TODO 滑动坐标
            context.tasker.controller.post_swipe(0, 0, 0, 0, 1, 1, 1).wait()
            time.sleep(interval)
    else:
        # 有限次数的旋转
        for _ in range(rotate_times):
            # 滑动时间：1，触控点：1 TODO 滑动坐标
            context.tasker.controller.post_swipe(0, 0, 0, 0, 1, 1, 1).wait()
            time.sleep(interval)
    return True
