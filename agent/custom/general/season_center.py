# 赛季中心相关逻辑
import time
import traceback

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.constant.key_event import ANDROID_KEY_EVENT_DATA
from agent.logger import logger
from .general import ensure_main_page
from .power_saving_mode import exit_power_saving_mode


# 打开赛季中心页面
@AgentServer.custom_action("open_season_center_page")
class OpenSeasonCenterAction(CustomAction):
    @exit_power_saving_mode()
    @ensure_main_page(strict=True)
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> None:
        try:
            # 发送 O 按键打开赛季中心
            context.tasker.controller.post_click_key(
                ANDROID_KEY_EVENT_DATA["KEYCODE_O"]
            ).wait()
            time.sleep(2)  # 等待页面加载
            # 验证是否成功打开赛季中心
            img = context.tasker.controller.post_screencap().wait().get()
            is_season_center: RecognitionDetail | None = context.run_recognition(
                "图片识别是否在赛季中心页面", img
            )
            if is_season_center and is_season_center.hit:
                logger.info("已成功打开赛季中心页面")
        except Exception as exc:
            logger.error(f"[OpenSeasonCenter] 打开赛季中心页面失败: {exc}")
            traceback.print_exc()


# 领取今日活跃度奖励
@AgentServer.custom_action("claim_today_activity_rewards")
class ClaimDailyActivityRewardAction(CustomAction):
    @exit_power_saving_mode()
    @ensure_main_page(strict=True)
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> None:
        try:
            # 打开赛季中心页面
            context.run_task(entry="打开赛季中心页面")
            time.sleep(1)
            # 领取每日活跃度奖励
            context.run_task(entry="依次领取各档位活跃度奖励")
            # 关闭赛季中心页面，返回主页面
            context.run_task(entry="回到主页面")
        except Exception as exc:
            logger.error(f"[ClaimDailyActivityReward] 领取每日活跃度奖励失败: {exc}")
            traceback.print_exc()


# 打开补偿商店页面
@AgentServer.custom_action("open_compensation_shop_page")
class OpenCompensationShopAction(CustomAction):
    @exit_power_saving_mode()
    @ensure_main_page(strict=True)
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> None:
        # 先打开赛季中心页面
        open_season_center_result = context.run_task(entry="打开赛季中心页面")
        if not open_season_center_result:
            logger.error(
                "[OpenCompensationShop] 无法打开补偿商店页面，打开赛季中心失败"
            )
            return
        # 点击补偿商店入口
        open_compensation_shop_result = context.run_task(
            entry="在赛季中心页面打开补偿商店页面"
        )
        if not open_compensation_shop_result:
            logger.error("[OpenCompensationShop] 无法打开补偿商店页面，点击入口失败")
            return
        logger.info("已成功打开补偿商店页面")


# 在玩法补偿商店页面购买所有可购买的补偿商品
@AgentServer.custom_action("buy_all_gameplay_compensation_shop_items")
class BuyAllGameplayCompensationShopItemsAction(CustomAction):
    @exit_power_saving_mode()
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> None:
        try:
            # 打开补偿商店页面
            context.run_task(entry="打开补偿商店页面")
            time.sleep(1)
            # 购买所有可购买的补偿商品
            context.run_task(entry="购买所有可购买的玩法补偿商店商品")
            # 关闭补偿商店页面，返回主页面
            context.run_task(entry="回到主页面")
        except Exception as exc:
            logger.error(
                f"[BuyAllGameplayCompensationShopItems] 购买所有可购买的玩法补偿商店商品失败: {exc}"
            )
            traceback.print_exc()
