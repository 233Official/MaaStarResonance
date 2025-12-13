import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.attach.common_attach import get_chat_channel, get_chat_loop_interval, get_chat_loop_limit, \
    get_chat_message_content, \
    get_chat_channel_id_list
from agent.constant.world_channel import CHANNEL_DATA
from agent.custom.general.power_saving_mode import default_exit_power_save
from agent.logger import logger


# 循环发送聊天频道消息
@AgentServer.custom_action("SendMessageLoop")
class SendMessageLoopAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        # 循环周期间隔时间
        loop_interval = get_chat_loop_interval(context)
        if loop_interval and loop_interval < 30:
            logger.error("如需设置循环周期间隔，则时间必须大于30秒")
            return False
        # 发送消息次数上限
        limit = get_chat_loop_limit(context)
        return send_message_loop(context, loop_interval, limit)


# 发送聊天频道消息
@AgentServer.custom_action("SendMessage")
class SendMessageAction(CustomAction):

    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        return send_message(context)


# 发送循环消息
def send_message_loop(context: Context, loop_interval, limit, check_interval = 2) -> bool:
    """
    发送循环消息

    Args:
        context: 控制器上下文
        loop_interval: 发送消息任务循环间隔
        limit: 发送消息次数上限
        check_interval: 检查间隔，默认2秒一次
    """
    # 已发送次数
    send_count = 0
    # 距离上次发送已经等待的时间
    elapsed = loop_interval

    # 循环发送
    while not context.tasker.stopping:
        if 0 < limit <= send_count:
            break

        # 每 2 秒检测一次状态
        time.sleep(check_interval)
        elapsed += check_interval

        # 只有当累计等待时间达到或超过 loop_interval 才发送
        if elapsed >= loop_interval:
            send_message(context)
            send_count += 1
            # 把已累计时间清零（或减去一个周期，用于更精细的补偿）
            elapsed = 0
            logger.info(f"[循环消息] 已完成发送消息 {send_count} 轮")
    return True


# 发送消息
def send_message(context: Context) -> bool:
    # 退出省电模式
    default_exit_power_save(context)

    # 本轮成功次数
    success_count = 0

    # 0. 变量检查
    message_content = get_chat_message_content(context)
    if not message_content:
        logger.error("需要发送的消息内容为空，请先设置内容")
        return False
    channel_name = get_chat_channel(context)
    channel_id_list = get_chat_channel_id_list(context)

    # 1. 检测并打开聊天框
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    chat_button: RecognitionDetail | None = context.run_recognition("检测聊天按钮", img)
    if not chat_button or not chat_button.hit:
        logger.error("未检测到聊天按钮，无法发送消息")
        return False
    context.tasker.controller.post_click(490, 600).wait()

    # 2. 切换到对应频道
    wait_times = 0
    need_next = False
    channel_dict = CHANNEL_DATA.get(channel_name, {})
    x, y, w, h = channel_dict["roi"]
    channel_id_dict = channel_dict.get("channel", {})
    while wait_times <= 10 and not context.tasker.stopping:
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        world_chat: RecognitionDetail | None = context.run_recognition(
            "通用文字识别",
            img,
            pipeline_override={
                "通用文字识别": {"expected": channel_name, "roi": [x, y, w, h]}
            },
        )
        if world_chat and world_chat.hit:
            need_next = True
            break
        wait_times += 1
        time.sleep(2)
    if not need_next:
        logger.error(f"未检测到 {channel_name} 频道，无法发送消息")
        context.run_action("ESC")
        return False
        
    # 点击对应文字的中间位置
    point_x = int(x + w / 2)
    point_y = int(y + h / 2)
    context.tasker.controller.post_click(point_x, point_y).wait()

    # 如果不是世界频道就做个假的循环
    if not channel_id_dict:
        channel_id_list = ["0"]
    # 根据世界频道分线ID列表循环处理
    for channel_id in channel_id_list:
        if context.tasker.stopping:
            context.run_action("ESC")
            return True
        # 3. 切换世界频道分线
        need_next = change_channel(channel_id, channel_id_dict, context, 1)
        if not need_next:
            continue
        # 4. 点击输入框
        time.sleep(2)
        context.tasker.controller.post_click(275, 680).wait()
        # 5. 输入内容
        time.sleep(2)
        context.run_action("输入聊天框内容", pipeline_override={
            "输入聊天框内容": {
                "action": {
                    "type": "InputText",
                    "param": {
                        "input_text": message_content
                    }
                }
            }
        })
        # 6. 点击确定按钮
        time.sleep(2)
        context.tasker.controller.post_click(1217, 668).wait()
        # 7. 检测并点击发送图标
        time.sleep(2)
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        send_button: RecognitionDetail | None = context.run_recognition("检测发送消息按钮", img)
        if send_button and send_button.hit:
            context.tasker.controller.post_click(807, 681).wait()
            success_count += 1
            logger.info(f"已成功向 {channel_name} 频道 {channel_id} 发送消息内容")
        else:
            logger.error(f"向 {channel_name} 频道 {channel_id} 发送消息内容失败：识别不到发送按钮")

    logger.info(f"===== 本轮发送 {channel_name} 频道消息已经成功：{success_count} / {len(channel_id_list)} ====")
    time.sleep(2)
    context.run_action("ESC")
    return True


def change_channel(channel_id: str, channel_id_dict: dict, context: Context, interval: float = 0.5) -> bool:
    """
    根据 channel_id 切换频道

    Args:
        channel_id: 频道ID
        channel_id_dict: 频道ID坐标字典
        context: 控制器上下文
        interval: 每次按键之间的间隔秒数，默认 0.5

    Returns:
        切换成功与否
    """
    if not channel_id_dict:
        return True
    time.sleep(2)
    # 点击开始切换
    context.tasker.controller.post_click(275, 41).wait()
    time.sleep(2)
    # 输入
    for digit in channel_id:
        if digit not in channel_id_dict:
            continue
        x, y = channel_id_dict[digit]
        context.tasker.controller.post_click(x, y).wait()
        time.sleep(interval)
    # 切换
    time.sleep(2)
    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    switch_result: RecognitionDetail | None = context.run_recognition(
        "通用文字识别",
        img,
        pipeline_override={
            "通用文字识别": {"expected": "OK", "roi": [339, 192, 39, 31]}
        },
    )
    if switch_result and switch_result.hit:
        context.tasker.controller.post_click(359, 208).wait()
        logger.info(f"已成功切换到聊天世界频道: {channel_id}")
        return True

    logger.info(f"聊天世界频道: {channel_id} 切换失败")
    return False
