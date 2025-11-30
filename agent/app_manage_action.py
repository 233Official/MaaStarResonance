import time

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction
from maa.job import Job

from custom_param import CustomActionParam
from logger import logger


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


def get_login_timeout(context: Context) -> int:
    """获取登录超时时长参数"""
    login_timeout_node = context.get_node_data("获取参数-登录超时时长")
    login_timeout = login_timeout_node.get("attach", {}).get("login_timeout", 240) if login_timeout_node else 240
    logger.info(f"登录超时时长参数: {login_timeout}秒")
    return int(login_timeout)


def get_area_change_timeout(context: Context) -> int:
    """获取场景切换超时时长参数"""
    area_change_timeout_node = context.get_node_data("获取参数-场景切换超时时长")
    area_change_timeout = area_change_timeout_node.get("attach", {}).get("area_change_timeout", 90) if area_change_timeout_node else 90
    logger.info(f"场景切换超时时长参数: {area_change_timeout}秒")
    return int(area_change_timeout)


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
    login_timeout = get_login_timeout(context)
    area_change_timeout = get_area_change_timeout(context)
    start_time = time.time()
    need_next = False
    elapsed_time = 0

    # 先关闭星痕共鸣
    stop_target_app(context, app_package_name)
    
    # 等待5秒再启动星痕共鸣
    logger.info("等待5秒后启动星痕共鸣...")
    time.sleep(5)

    # 再启动星痕共鸣
    start_target_app(context, app_package_name)

    # 等待星痕共鸣启动完成
    logger.info("等待星痕共鸣已启动，等待游戏连接开始...")
    while elapsed_time <= login_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        login_result: RecognitionDetail | None = context.run_recognition("点击连接开始", img)
        if login_result and login_result.hit:
            del login_result
            logger.info("检测到主界面连接开始按钮，准备登录游戏...")
            context.tasker.controller.post_click(639, 602).wait()
            need_next = True
            break
        del login_result
        time.sleep(2)
    
    # 登录结果判断
    if not need_next:
        logger.error("星痕共鸣登录超时，未检测到连接开始按钮，请检查应用是否正常启动")
        return False
    
    logger.info("星痕共鸣连接开始完成，等待10秒后将检测进入游戏按钮...")
    time.sleep(10)

    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
    entry_result: RecognitionDetail | None = context.run_recognition("点击进入游戏", img)
    if not entry_result or not entry_result.hit:
        # 未识别到进入游戏，继续等待
        logger.error("未检测到进入游戏按钮，登录失败，请检查网络或应用状态！")
        return False
    
    # 识别到进入游戏，点击进入游戏
    context.tasker.controller.post_click(1103, 632).wait()
    logger.info("星痕共鸣进入游戏成功，将等待登录完成...")
    del entry_result

    # 等待进入游戏主页面
    start_time = time.time()
    elapsed_time = 0
    while elapsed_time <= area_change_timeout and not context.tasker.stopping:
        elapsed_time = time.time() - start_time
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        area_change_result: RecognitionDetail | None = context.run_recognition("图片识别是否在主页面", img)
        if area_change_result and area_change_result.hit:
            del area_change_result, img
            logger.info("检测到已经进入游戏主页面，登录成功！")
            return True
        del area_change_result, img
        time.sleep(2)

    # 超时未进入游戏主页面
    logger.error("星痕共鸣进入游戏超时，未检测到主页面，请检查应用状态！")
    return False
