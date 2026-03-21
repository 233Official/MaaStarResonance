import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.attach.common_attach import get_area_change_timeout, get_world_line_id_list
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.custom.general.power_saving_mode import default_exit_power_save
from agent.logger import logger


# 切换分线
@AgentServer.custom_action("SwitchLine")
class SwitchLineAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        line_list = get_world_line_id_list(context)
        return switch_line(context, line_list)

def switch_line(context: Context, line_list: list[str]) -> bool:
    """
    尝试根据列表切换分线，直到成功或列表为空

    Args:
        context: 控制器上下文
        line_list: 备选分线列表

    Returns: 是否完成

    """
    if not line_list:
        logger.error("分线列表不能为空！")
        return False

    # 是否正在尝试切换
    is_trying = False

    default_exit_power_save(context)

    for line_str in line_list:
        if context.tasker.stopping:
            return True
        # 按 P 键打开分线列表
        context.tasker.controller.post_click_key(ANDROID_KEY_EVENT_DATA["KEYCODE_P"]).wait()
        time.sleep(3)
        # 点击右下角输入框
        context.tasker.controller.post_click(989, 672).wait()
        time.sleep(3)
        # 输入分线名称
        context.run_action("输入聊天框内容", pipeline_override={
            "输入聊天框内容": {
                "action": {
                    "type": "InputText",
                    "param": {
                        "input_text": line_str
                    }
                }
            }
        })
        time.sleep(3)
        # 点击确定按钮
        context.tasker.controller.post_click(1217, 668).wait()
        time.sleep(3)
        # 点击前往分线
        context.tasker.controller.post_click(1189, 674).wait()
        time.sleep(3)
        # 检测是否正在切换场景
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        detail: RecognitionDetail | None = context.run_recognition(
            "图片识别是否在主页面", img
        )
        # 切换成功：跳出循环，否则继续循环下一个分线
        if detail and not detail.hit:
            is_trying = True
            break

    # 切换失败
    if not is_trying:
        logger.error(f"分线列表中所有分线均切换失败！")
        # 切换失败了需要再按一下 P 返回
        context.tasker.controller.post_click_key(ANDROID_KEY_EVENT_DATA["KEYCODE_P"]).wait()
        time.sleep(1)
        return False

    # 场景切换超时时间
    area_change_timeout = get_area_change_timeout(context)
    # 等待场景切换完成
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            del area_change_result, img
            logger.info(f"检测到已经成功切换场景，分线切换已完成！")
            return True
        del area_change_result, img
        time.sleep(2)

    # 超时场景未切换完成
    logger.error(f"切换场景超时，未检测到主页面，请检查应用状态！")
    return False
