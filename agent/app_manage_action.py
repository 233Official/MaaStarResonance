from maa.agent.agent_server import AgentServer
from maa.context import Context
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
        job: Job = context.tasker.controller.post_start_app(app_package_name).wait()
        if job.succeeded:
            logger.info(f"已启动应用: {app_package_name}")
            return True
        else:
            logger.error(f"启动应用失败: {app_package_name}，请检查应用包名是否正确")
            return False


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
        job: Job = context.tasker.controller.post_stop_app(app_package_name).wait()
        if job.succeeded:
            logger.info(f"已关闭应用: {app_package_name}")
            return True
        else:
            logger.error(f"关闭应用失败: {app_package_name}，请检查应用包名是否正确")
            return False


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
        stop_job: Job = context.tasker.controller.post_stop_app(app_package_name).wait()
        if not stop_job.succeeded:
            logger.error(f"重启应用失败: {app_package_name}，关闭应用时出错，请检查应用包名是否正确")
            return False
        start_job: Job = context.tasker.controller.post_start_app(app_package_name).wait()
        if start_job.succeeded:
            logger.info(f"已重启应用: {app_package_name}")
            return True
        else:
            logger.error(f"重启应用失败: {app_package_name}，启动应用时出错，请检查应用包名是否正确")
            return False
