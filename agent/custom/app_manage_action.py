import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction
from maa.job import Job

from agent.attach.common_attach import get_area_change_timeout, get_login_timeout
from agent.logger import logger
from agent.utils.param_utils import CustomActionParam


# 启动指定APP
@AgentServer.custom_action("StartTargetApp")
class StartTargetAppAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        required = params.require(["app_package_name"])
        app_package_name = required["app_package_name"]
        return start_target_app(context, app_package_name)


# 关闭指定APP
@AgentServer.custom_action("StopTargetApp")
class StopTargetAppAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        required = params.require(["app_package_name"])
        app_package_name = required["app_package_name"]
        return stop_target_app(context, app_package_name)


# 重启指定APP
@AgentServer.custom_action("RestartTargetApp")
class RestartTargetAppAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取参数
        params = CustomActionParam(argv.custom_action_param)
        required = params.require(["app_package_name"])
        app_package_name = required["app_package_name"]

        # 先关闭应用
        stop_target_app(context, app_package_name)
        
        # 等待5秒再启动应用
        logger.info("等待5秒后启动应用...")
        time.sleep(5)

        # 再启动应用
        return start_target_app(context, app_package_name)


# 重启并登录星痕共鸣
@AgentServer.custom_action("RestartAndLoginXHGM")
class RestartAndLoginXHGMAction(CustomAction):
    def run(
        self,
        context: Context,
        _,
    ) -> bool:
        return restart_and_login_xhgm(context)


def start_target_app(context: Context, app_package_name: str) -> bool:
    """启动指定应用"""
    job: Job = context.tasker.controller.post_start_app(app_package_name).wait()
    if job.succeeded:
        logger.info(f"已启动应用: {app_package_name}")
        return True
    else:
        logger.error(f"启动应用失败: {app_package_name}，请检查应用包名是否正确")
        return False


def stop_target_app(context: Context, app_package_name: str) -> bool:
    """关闭指定应用"""
    job: Job = context.tasker.controller.post_stop_app(app_package_name).wait()
    if job.succeeded:
        logger.info(f"已关闭应用: {app_package_name}")
        return True
    else:
        logger.error(f"关闭应用失败: {app_package_name}，请检查应用包名是否正确")
        return False


def restart_and_login_xhgm(context: Context) -> bool:
    """重启并登录星痕共鸣"""
    app_package_name = "com.tencent.wlfz"

    # 先关闭星痕共鸣
    stop_target_app(context, app_package_name)
    
    # 等待5秒再启动星痕共鸣
    logger.info("等待5秒后启动星痕共鸣...")
    time.sleep(5)

    # 再启动星痕共鸣
    start_target_app(context, app_package_name)

    # 等待星痕共鸣启动完成
    logger.info("等待星痕共鸣已启动，等待游戏连接开始...")
    need_next = wait_for_start(context)
    
    # 登录结果判断
    if not need_next:
        return False

    logger.info("等待8秒后将检测进入游戏按钮...")
    time.sleep(8)

    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    entry_result: RecognitionDetail | None = context.run_recognition("点击进入游戏", img)
    if not entry_result or not entry_result.hit:
        # 未识别到进入游戏
        logger.error("未检测到进入游戏按钮，登录失败，请检查网络或应用状态！")
        return False
    
    # 识别到进入游戏，点击进入游戏
    context.tasker.controller.post_click(1103, 632).wait()
    logger.info("星痕共鸣进入游戏成功，将等待登录完成...")
    del entry_result

    # 等待进入游戏主界面
    return wait_for_switch(context)


def wait_for_start(context: Context) -> bool:
    """等待游戏启动"""
    login_timeout = get_login_timeout(context)
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= login_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        # 登录完成检测
        login_result: RecognitionDetail | None = context.run_recognition("点击连接开始", img)
        if login_result and login_result.hit:
            del login_result, img
            logger.info("检测到星痕共鸣已经成功启动完游戏！")
            context.tasker.controller.post_click(639, 602).wait()
            return True
        # 登录信息失效检测
        no_login_result: RecognitionDetail | None = context.run_recognition("检测是否需要登录", img)
        if no_login_result and no_login_result.hit:
            del login_result, no_login_result, img
            logger.info("检测到星痕共鸣登录信息失效，需要登录账号！")
            return False
        del login_result, no_login_result, img
        time.sleep(2)
    logger.error(f"星痕共鸣启动游戏超{login_timeout}秒限制 或者 被手动停止，请检查游戏状态！")
    return False


def wait_for_switch(context: Context) -> bool:
    """等待场景切换"""
    area_change_timeout = get_area_change_timeout(context)
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            del area_change_result, img
            logger.info("检测到星痕共鸣已经成功切换场景！")
            return True
        del area_change_result, img
        time.sleep(2)
    # 超时未进入游戏主页面
    logger.error(f"星痕共鸣切换场景超过{area_change_timeout}秒限制 或者 被手动停止，请检查游戏状态！")
    return False
