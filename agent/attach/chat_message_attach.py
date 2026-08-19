from maa.context import Context

from agent.attach import attach_param, attach_param_list


@attach_param("获取参数-聊天框发消息的次数上限", "limit", 0, int)
def get_chat_loop_limit(context: Context) -> int:
    """获取聊天框发消息的次数上限参数"""
    ...


@attach_param("获取参数-聊天框发消息的周期", "loop_interval", 120, int)
def get_chat_loop_interval(context: Context) -> int:
    """获取聊天框发消息的周期参数"""
    ...


@attach_param("获取参数-输入聊天框频道", "channel", "世界")
def get_chat_channel(context: Context) -> str:
    """获取聊天框频道参数"""
    ...


@attach_param_list("获取参数-需要发送消息的世界频道分线ID", "channel_ids")
def get_chat_channel_id_list(context: Context) -> list[str]:
    """获取需要发送消息的世界频道分线ID参数"""
    ...


@attach_param("获取参数-输入聊天框的消息内容", "content", "")
def get_chat_message_content(context: Context) -> str:
    """获取输入聊天框的消息内容参数"""
    ...


@attach_param("获取参数-需要发送的消息是否需要队伍人数信息", "need_number", False, bool)
def get_chat_message_need_team(context: Context) -> bool:
    """获取需要发送的消息是否需要队伍人数信息参数"""
    ...


@attach_param("获取参数-队伍已满时是否还需要发送消息", "force_send", False, bool)
def get_full_team_force_send(context: Context) -> bool:
    """获取队伍已满时是否还需要发送消息参数"""
    ...
