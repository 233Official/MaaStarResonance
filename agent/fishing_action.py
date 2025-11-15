import time
import traceback

import numpy
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, RecognitionResult
from maa.custom_action import CustomAction

from logger import logger


# 自动钓鱼任务
@AgentServer.custom_action("AutoFishing")
class AutoFishingAction(CustomAction):

    def __init__(self):
        super().__init__()
        # 当前钓鱼次数
        self.fishing_count = 1
        # 收竿触控通道常量
        self.REEL_IN_CONTACT = 0
        # 方向触控通道常量
        self.BOWING_CONTACT = 1

    def run(
        self,
        context: Context,
        _: CustomAction.RunArg,
    ) -> bool:
        """
        超究极无敌变异进化全自动钓鱼
        """
        
        # 1. 判断省电模式 | 失败也不要紧，说明不在省电模式
        context.run_action("从省电模式唤醒")
        time.sleep(1)

        # 2. 首次钓鱼：检测进入钓鱼按钮 和 检测抛竿按钮 至少得有一个检测成功 | 不然没法钓鱼
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        fishing_result: RecognitionDetail | None = context.run_recognition("检测进入钓鱼按钮", img)
        if fishing_result and fishing_result.hit:
            logger.info("正在进入钓鱼台，等待5秒...")
            context.run_action("点击进入钓鱼按钮")
            time.sleep(5)
        else:
            logger.warning('没有检测到进入钓鱼台按钮，可能是已经在钓鱼中，将直接检测抛竿按钮')


        # 第二重抛竿按钮检测
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        reeling_result: RecognitionDetail | None = context.run_recognition("检测抛竿按钮", img)
        if fishing_result and fishing_result.hit and reeling_result and not reeling_result.hit:
            logger.exception('已进入钓鱼台，但是没有检测到抛竿按钮，未知原因！')  # TODO 是否需要通过循环检测保证稳定性
            return False
        elif fishing_result and not fishing_result.hit and reeling_result and not reeling_result.hit:
            logger.exception('没有检测到进入钓鱼台按钮，也没有检测到抛竿按钮，请检查是否在钓鱼地点！')
            return False
        time.sleep(3)

        # 开始钓鱼循环
        while True:
            logger.info(f"> 正在进行第{str(self.fishing_count)}次钓鱼...")
            try:
                # 3. 检测配件：点击添加鱼竿 和 点击添加鱼饵 都检测失败 | 才说明不需要买鱼竿和鱼饵就可以正常钓鱼
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                rod_result: RecognitionDetail | None = context.run_recognition("检测是否需要添加鱼竿", img)
                # 需要添加鱼竿
                if rod_result and rod_result.hit:
                    logger.info("检测到：需要添加鱼竿")
                    context.run_action("点击添加鱼竿")
                    time.sleep(1)
                    # 检测一下是否还有已有的鱼竿：有前往购买说明没有了，没有按钮说明还有鱼竿
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    buy_rod_result: RecognitionDetail | None = context.run_recognition("检测是否需要购买鱼竿", img)
                    # 需要购买鱼竿
                    if buy_rod_result and buy_rod_result.hit:
                        logger.info("检测到：鱼竿不足，需要购买")
                        context.run_action("点击前往购买鱼竿页面")
                        time.sleep(3)
                        # 选择并购买鱼竿
                        context.run_action("选择并购买需要的鱼竿")
                        time.sleep(1)
                        context.run_action("点击钓鱼配件购买按钮")
                        logger.info("1个鱼竿购买完成，返回钓鱼界面")
                        time.sleep(1)
                        # ESC
                        context.run_action("ESC")
                        time.sleep(1)
                        # 购买完再次检测后点击添加按钮
                        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                        context.run_recognition("检测是否需要添加鱼竿", img)
                        context.run_action("点击添加鱼竿")
                        time.sleep(1)
                    # 点击使用鱼竿
                    logger.info("点击使用已有的鱼竿")
                    context.run_action("点击使用鱼竿")
                    time.sleep(1)
                
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                bait_result: RecognitionDetail | None = context.run_recognition("检测是否需要添加鱼饵", img)
                # 需要添加鱼饵
                if bait_result and bait_result.hit:
                    logger.info("检测到：需要添加鱼饵")
                    context.run_action("点击添加鱼饵")
                    time.sleep(1)
                    # 检测一下是否还有已有的鱼饵：有前往购买说明没有了，没有按钮说明还有鱼饵
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    buy_bait_result: RecognitionDetail | None = context.run_recognition("检测是否需要购买鱼饵", img)
                    # 需要购买鱼饵
                    if buy_bait_result and buy_bait_result.hit:
                        logger.info("检测到：鱼饵不足，需要购买")
                        context.run_action("点击前往购买鱼饵页面")
                        time.sleep(3)
                        # 选择并购买鱼饵 | 默认买最大数量：200个
                        context.run_action("选择并购买需要的鱼饵")
                        time.sleep(1)
                        context.run_action("点击钓鱼配件最大数量按钮")
                        time.sleep(1)
                        context.run_action("点击钓鱼配件购买按钮")
                        logger.info("200个鱼饵购买完成，返回钓鱼界面")
                        time.sleep(1)
                        # ESC
                        context.run_action("ESC")
                        time.sleep(1)
                        # 购买完再次检测后点击添加按钮
                        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                        context.run_recognition("检测是否需要添加鱼饵", img)
                        context.run_action("点击添加鱼饵")
                        time.sleep(1)
                    # 点击使用鱼饵
                    logger.info("点击使用已有的鱼饵")
                    context.run_action("点击使用鱼饵")
                    time.sleep(1)
                
                # 4. 开始抛竿
                logger.info("开始抛竿，等待鱼鱼上钩...")
                context.run_action("点击抛竿按钮")
                time.sleep(1)

                # 5. 检测鱼鱼是否上钩 | 检测30秒
                wait_for_fish_times = 0
                while wait_for_fish_times < 300:
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    is_hooked: RecognitionDetail | None = context.run_recognition("检测鱼鱼是否上钩", img)
                    if is_hooked and is_hooked.hit:
                        logger.info("鱼鱼上钩了！")
                        break
                    time.sleep(0.1)
                    wait_for_fish_times += 1

                # 6. 开始收线：没箭头一直按，有箭头按3秒停0.5秒再继续按3秒停0.5秒，但是如果显示了箭头就立刻停0.5秒，再按3秒停0.5秒 | 方向键：没箭头不动，有箭头按3秒后停止不按
                self._reelLoop(context)
                self.fishing_count += 1

                # 7. 本次钓鱼完成，检测并点击继续钓鱼按钮进行第二次钓鱼
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                is_continue_fishing: RecognitionDetail | None = context.run_recognition("检测继续钓鱼", img)
                if is_continue_fishing and is_continue_fishing.hit:
                    logger.info("检测到继续钓鱼按钮，2秒后将开始下一次钓鱼")
                    time.sleep(2)
                    context.run_action("点击继续钓鱼按钮")
                    time.sleep(2)


            except Exception as exc:
                stack_trace = traceback.format_exc()
                logger.exception(
                    f"run pipeline node AutoFishing failed, error: {exc}\n{stack_trace}",
                )
                return False

    def _reelLoop(self, context: Context):
        """
        钓鱼循环逻辑（收线和方向键并行处理）
        """
        # ------- 情况检测 -------
        not_reeling_count = 0       # 连续检测到不在收线的次数
        not_reeling_threshold = 15  # 阈值，例如连续几次不在收线才退出

        # ------- 收线状态 -------
        pressing_reel = False       # 是否在按收线键
        cycle_start = None          # 当前节奏循环起点时间（第一次进来为空）
        pause_duration = 0.1        # 停 0.1 秒
        press_duration = 3.0        # 按 3 秒
        arrow_present_last = False  # 前一次是否有箭头

        # ------- 方向状态 -------
        bow_pressing = False        # 是否再按方向键
        bow_release_time = 0        # 方向松开时间戳
        current_bow_dir = None      # 当前

        while True:
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
            # 获取箭头方向
            bow_direction = self.get_bow_direction(context, img)
            if bow_direction:
                logger.info(f"当前箭头方向：{bow_direction}")

            # 检查是否还在钓鱼
            is_reeling_icon = self.check_if_reeling(context, img)
            if not is_reeling_icon:
                not_reeling_count += 1
            else:
                not_reeling_count = 0

            if not_reeling_count >= not_reeling_threshold:
                logger.info("检测到：已经不在收线状态，可能是本次钓鱼已完成，等待3秒后进行下一次钓鱼...")
                # 停掉动作
                if pressing_reel:
                    self.stop_reel_in(context)
                if bow_pressing:
                    self.stop_bow(context)
                time.sleep(3)
                return

            now = time.time()

            # ========= 收线逻辑 =========
            if cycle_start is None and bow_direction is None:
                # 第一次进来且无箭头 → 一直按
                if not pressing_reel:
                    self.start_reel_in(context)
                    pressing_reel = True
                # 不进入循环模式
            elif bow_direction is not None and not arrow_present_last:
                # 第一次出现箭头：进入循环，先停一下
                if pressing_reel:
                    self.stop_reel_in(context)
                    pressing_reel = False
                cycle_start = now  # 重置循环起点
                arrow_present_last = True
                logger.info("箭头出现 -> 立即停一下开始循环模式")
            elif bow_direction is not None and arrow_present_last and current_bow_dir != bow_direction:
                # 箭头方向变化（或箭头再次出现） → 立即停一下，然后重置循环
                if pressing_reel:
                    self.stop_reel_in(context)
                    pressing_reel = False
                cycle_start = now
                logger.info("箭头方向变化 -> 立即停一下重置循环")
            elif bow_direction is None and arrow_present_last:
                # 箭头消失但已经在循环模式中，继续节奏，不退出
                arrow_present_last = False

            # 循环模式的按停逻辑（仅当 cycle_start 有值）
            if cycle_start is not None:
                elapsed = (now - cycle_start) % (press_duration + pause_duration)
                if elapsed < press_duration:
                    if not pressing_reel:
                        self.start_reel_in(context)
                        pressing_reel = True
                        logger.debug("循环模式：开始收线")
                else:
                    if pressing_reel:
                        self.stop_reel_in(context)
                        pressing_reel = False
                        logger.debug("循环模式：停止收线")

            # ========= 方向逻辑 =========
            if bow_direction is not None:
                if current_bow_dir != bow_direction:
                    if bow_pressing:
                        self.stop_bow(context)
                    if self.start_bow(context, bow_direction):
                        bow_pressing = True
                        bow_release_time = now + 3.0
                        current_bow_dir = bow_direction
                        logger.info("方向键按下 3 秒")
                    else:
                        bow_pressing = False
                else:
                    if bow_pressing and now >= bow_release_time:
                        self.stop_bow(context)
                        bow_pressing = False
                        logger.info("方向键松开")
            else:
                if bow_pressing and now >= bow_release_time:
                    self.stop_bow(context)
                    bow_pressing = False

            # 刷新状态检测
            time.sleep(pause_duration)

    @staticmethod
    def check_if_reeling(context: Context, img: numpy.ndarray) -> bool:
        """
        检查当前是否在收线
        """
        recognition_task: RecognitionDetail | None = context.run_recognition("检查当前是否在收线", img)
        if not recognition_task:
            return False
        filtered_list = recognition_task.filterd_results
        is_reeling = len(filtered_list) > 0
        return is_reeling

    @staticmethod
    def get_bow_direction(context: Context, img: numpy.ndarray) -> str | None:
        """
        获取箭头方向（left/right 或 None）
        """
        bow_left_task: RecognitionDetail | None = context.run_recognition("检查向左箭头", img)
        bow_right_task: RecognitionDetail | None = context.run_recognition("检查向右箭头", img)
        if not bow_left_task or not bow_right_task:
            return None

        # 最好的识别结果
        bow_left_best: RecognitionResult | None = bow_left_task.best_result
        bow_right_best: RecognitionResult | None = bow_right_task.best_result

        # 判断左右
        bow_left_score = bow_left_best.score if bow_left_best else 0  # type: ignore
        bow_right_score = bow_right_best.score if bow_right_best else 0  # type: ignore

        if bow_left_score > bow_right_score:
            return "left"
        elif bow_right_score > bow_left_score:
            return "right"
        else:
            return None

    def start_reel_in(self, context: Context) -> bool:
        """
        开始收线动作
        """
        result = context.tasker.controller.post_touch_down(1160, 585, self.REEL_IN_CONTACT, 1).wait()
        return result.succeeded

    def stop_reel_in(self, context: Context) -> bool:
        """
        停止收线动作
        """
        result = context.tasker.controller.post_touch_up(self.REEL_IN_CONTACT).wait()
        return result.succeeded

    def start_bow(self, context: Context, direction: str) -> bool:
        """
        开始箭头转向动作
        """
        x = 150 if direction == "left" else 320
        y = 530
        result = context.tasker.controller.post_touch_down(x, y, self.BOWING_CONTACT, 1).wait()
        return result.succeeded

    def stop_bow(self, context: Context) -> bool:
        """
        停止箭头转向动作
        """
        result = context.tasker.controller.post_touch_up(self.BOWING_CONTACT).wait()
        return result.succeeded
