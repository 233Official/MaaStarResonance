import numpy
from logger import logger
import traceback
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail, ActionDetail
from maa.custom_action import CustomAction


# 自动钓鱼任务
@AgentServer.custom_action("AutoFishing")
class AutoFishingAction(CustomAction):

    def __init__(self):
        super().__init__()
        # 当前钓鱼次数
        self.fishing_count = 1
        # 是否正在拉竿
        self._isReelingIn = False
        # 当前箭头方向
        self._currentBowDirection = None
        # 上次箭头方向变化时间
        self._lastBowDirectionChangeTime = 0
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
        _: ActionDetail = context.run_action("从省电模式唤醒")
        time.sleep(1)

        # 2. 首次钓鱼：检测进入钓鱼按钮 和 检测抛竿按钮 至少得有一个检测成功 | 不然没法钓鱼
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        fishing_result: RecognitionDetail = context.run_recognition("检测进入钓鱼按钮", img)
        if not fishing_result.hit:
            logger.warning('没有检测到进入钓鱼台按钮，可能是已经在钓鱼中，将检测抛竿按钮')
        _: ActionDetail = context.run_action("点击进入钓鱼按钮")
        time.sleep(3)

        # 第二重抛竿按钮检测
        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
        reeling_result: RecognitionDetail = context.run_recognition("检测抛竿按钮", img)
        if fishing_result.hit and not reeling_result.hit:
            logger.exception('已进入钓鱼台，但是没有检测到抛竿按钮，未知原因！')  # TODO 是否需要通过循环检测保证稳定性
            return False
        elif not fishing_result.hit and not reeling_result.hit:
            logger.exception('没有检测到进入钓鱼台按钮，也没有检测到抛竿按钮，请检查是否在钓鱼地点！')
            return False
        time.sleep(3)

        # 开始钓鱼循环
        while True:
            logger.info(f"> 正在进行第{str(self.fishing_count)}次钓鱼...")
            try:
                # 3. 检测配件：点击添加鱼竿 和 点击添加鱼饵 都检测失败 | 才说明不需要买鱼竿和鱼饵就可以正常钓鱼
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                rod_result: RecognitionDetail = context.run_recognition("检测是否需要添加鱼竿", img)
                # 需要添加鱼竿
                if rod_result.hit:
                    logger.info("检测到：需要添加鱼竿")
                    _: ActionDetail = context.run_action("点击添加鱼竿")
                    time.sleep(1)
                    # 检测一下是否还有已有的鱼竿：有前往购买说明没有了，没有按钮说明还有鱼竿
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    buy_rod_result: RecognitionDetail = context.run_recognition("检测是否需要购买鱼竿", img)
                    # 需要购买鱼竿
                    if buy_rod_result.hit:
                        logger.info("检测到：鱼竿不足，需要购买")
                        _: ActionDetail = context.run_action("点击前往购买鱼竿页面")
                        time.sleep(3)
                        # 选择并购买鱼竿
                        _: ActionDetail = context.run_action("选择并购买需要的鱼竿")
                        time.sleep(1)
                        _: ActionDetail = context.run_action("点击钓鱼配件购买按钮")
                        logger.info("1个鱼竿购买完成，返回钓鱼界面")
                        time.sleep(1)
                        # ESC
                        _: ActionDetail = context.run_action("ESC")
                        time.sleep(1)
                        # 购买完再次检测后点击添加按钮
                        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                        _: RecognitionDetail = context.run_recognition("检测是否需要添加鱼竿", img)
                        _: ActionDetail = context.run_action("点击添加鱼竿")
                        time.sleep(1)
                    # 点击使用鱼竿
                    logger.info("点击使用已有的鱼竿")
                    _: ActionDetail = context.run_action("点击使用鱼竿")
                    time.sleep(1)
                
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                bait_result: RecognitionDetail = context.run_recognition("检测是否需要添加鱼饵", img)
                # 需要添加鱼饵
                if bait_result.hit:
                    logger.info("检测到：需要添加鱼饵")
                    _: ActionDetail = context.run_action("点击添加鱼饵")
                    time.sleep(1)
                    # 检测一下是否还有已有的鱼饵：有前往购买说明没有了，没有按钮说明还有鱼饵
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    buy_bait_result: RecognitionDetail = context.run_recognition("检测是否需要购买鱼饵", img)
                    # 需要购买鱼饵
                    if buy_bait_result.hit:
                        logger.info("检测到：鱼饵不足，需要购买")
                        _: ActionDetail = context.run_action("点击前往购买鱼饵页面")
                        time.sleep(3)
                        # 选择并购买鱼饵 | 默认买最大数量：200个
                        _: ActionDetail = context.run_action("选择并购买需要的鱼饵")
                        time.sleep(1)
                        _: ActionDetail = context.run_action("点击钓鱼配件最大数量按钮")
                        time.sleep(1)
                        _: ActionDetail = context.run_action("点击钓鱼配件购买按钮")
                        logger.info("200个鱼饵购买完成，返回钓鱼界面")
                        time.sleep(1)
                        # ESC
                        _: ActionDetail = context.run_action("ESC")
                        time.sleep(1)
                        # 购买完再次检测后点击添加按钮
                        img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                        _: RecognitionDetail = context.run_recognition("检测是否需要添加鱼饵", img)
                        _: ActionDetail = context.run_action("点击添加鱼饵")
                        time.sleep(1)
                    # 点击使用鱼饵
                    logger.info("点击使用已有的鱼饵")
                    _: ActionDetail = context.run_action("点击使用鱼饵")
                    time.sleep(1)
                
                # 4. 开始抛竿
                logger.info("开始抛竿，等待鱼鱼上钩...")
                _: ActionDetail = context.run_action("点击抛竿按钮")
                time.sleep(1)

                # 5. 检测鱼鱼是否上钩 | 检测30秒
                wait_for_fish_times = 0
                while wait_for_fish_times < 300:
                    img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                    is_hooked: RecognitionDetail = context.run_recognition("检测鱼鱼是否上钩", img)
                    if is_hooked.hit:
                        logger.info("鱼鱼上钩了！")
                        break
                    time.sleep(0.1)
                    wait_for_fish_times += 1

                # 6. 开始收线：没箭头一直按，有箭头按3秒停0.5秒再继续按3秒停0.5秒，但是如果显示了箭头就立刻停0.5秒，再按3秒停0.5秒 | 方向键：没箭头不动，有箭头按3秒后停止不按
                self._reelLoop(context)
                self.fishing_count += 1

                # 7. 本次钓鱼完成，检测并点击继续钓鱼按钮进行第二次钓鱼
                img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()
                is_continue_fishing: RecognitionDetail = context.run_recognition("检测继续钓鱼", img)
                if is_continue_fishing.hit:
                    logger.info("检测到继续钓鱼按钮，将开始下一次钓鱼")
                    _: ActionDetail = context.run_action("点击继续钓鱼按钮")
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
        not_reeling_count = 0  # 连续检测到不在收线的次数
        not_reeling_threshold = 15  # 阈值，例如连续几次不在收线才退出

        # ------- 收线状态 -------
        reel_mode = "no_arrow"  # no_arrow:没箭头按住, arrow_cycle:有箭头按3停0.5循环
        pressing_reel = False
        reel_pause_until = 0  # 暂停结束时间戳
        reel_press_until = 0  # 按住结束时间戳

        # ------- 方向状态 -------
        bow_pressing = False
        bow_release_time = 0  # 方向松开时间戳
        current_bow_dir = None

        while True:
            img: numpy.ndarray = context.tasker.controller.post_screencap().wait().get()

            # 获取箭头方向
            bow_direction = self.getBowDirection(context, img)
            logger.info(f"当前箭头方向：{bow_direction}")

            # 检查是否还在钓鱼 | 第一次进来不检测
            is_reeling_icon = self.checkIfReeling(context, img)
            if not is_reeling_icon:
                not_reeling_count += 1
            else:
                not_reeling_count = 0

            if not_reeling_count >= not_reeling_threshold:
                logger.info("检测到：已经不在收线状态，可能是本次钓鱼已完成，等待3秒后进行下一次钓鱼...")
                # 停掉动作
                if pressing_reel:
                    self.stopReelIn(context)
                    pressing_reel = False
                if bow_pressing:
                    self.stopBow(context)
                    bow_pressing = False
                time.sleep(3)
                return

            now = time.time()

            # ========= 收线逻辑 =========
            if bow_direction is None:
                # 没箭头：一直按收线
                if not pressing_reel:
                    logger.info("收线按钮-普通模式：一直按收线")
                    self.startReelIn(context)
                    pressing_reel = True
                reel_mode = "no_arrow"
            else:
                if reel_mode != "arrow_cycle":
                    # 第一次进入有箭头模式 → 停0.5秒
                    if pressing_reel:
                        logger.info("收线按钮-有箭头模式：第一次进入 → 停0.5秒")
                        self.stopReelIn(context)
                        pressing_reel = False
                    reel_pause_until = now + 0.5
                    reel_mode = "arrow_cycle"
                else:
                    if now < reel_pause_until:
                        # 暂停阶段
                        if pressing_reel:
                            logger.info("收线按钮-有箭头模式：停0.5秒")
                            self.stopReelIn(context)
                            pressing_reel = False
                    else:
                        if not pressing_reel:
                            # 开始按
                            logger.info("收线按钮-有箭头模式：按住3秒")
                            self.startReelIn(context)
                            pressing_reel = True
                            reel_press_until = now + 3.0
                        elif pressing_reel and now >= reel_press_until:
                            # 停止按
                            logger.info("收线按钮-有箭头模式：停0.5秒")
                            self.stopReelIn(context)
                            pressing_reel = False
                            reel_pause_until = now + 0.5

            # ========= 方向逻辑 =========
            if bow_direction is None:
                # 没箭头: 松开方向
                if bow_pressing:
                    logger.info("方向键-普通模式：松开方向")
                    self.stopBow(context)
                    bow_pressing = False
                current_bow_dir = None
            else:
                if current_bow_dir != bow_direction:
                    # 方向第一次出现或变化
                    if bow_pressing:
                        logger.info("方向键-有箭头模式：先松开方向")
                        self.stopBow(context)
                    if self.startBow(context, bow_direction):
                        logger.info("方向键-有箭头模式：再转向3秒")
                        bow_pressing = True
                        bow_start_time = now
                        bow_release_time = now + 3.0
                        current_bow_dir = bow_direction
                    else:
                        bow_pressing = False
                else:
                    # 同一方向按了 >=3秒则松开
                    if bow_pressing and now >= bow_release_time:
                        logger.info("方向键-有箭头模式：松开方向")
                        self.stopBow(context)
                        bow_pressing = False

            # 每100ms刷新一次状态
            time.sleep(0.1)

    def checkIfReeling(self, context: Context, img: numpy.ndarray) -> bool:
        """
        检查当前是否在收线
        """
        recognition_task: RecognitionDetail = context.run_recognition(
            "检查当前是否在收线", img
        )
        filtered_list = recognition_task.filterd_results
        is_reeling = len(filtered_list) > 0
        logger.debug(f"检测是否在收线: {is_reeling}")
        return is_reeling

    def getBowDirection(self, context: Context, img: numpy.ndarray) -> str | None:
        """
        获取箭头方向（left/right 或 None）
        """
        bow_left_task: RecognitionDetail = context.run_recognition("检查向左箭头", img)
        bow_right_task: RecognitionDetail = context.run_recognition("检查向右箭头", img)

        # 最好的识别结果
        bow_left_best = bow_left_task.best_result
        bow_right_best = bow_right_task.best_result

        # 判断左右
        bow_left_score = bow_left_best.score if bow_left_best else 0
        bow_right_score = bow_right_best.score if bow_right_best else 0

        if bow_left_score > bow_right_score:
            return "left"
        elif bow_right_score > bow_left_score:
            return "right"
        else:
            return None

    def startReelIn(self, context: Context) -> bool:
        """
        开始收线动作
        """
        result = context.tasker.controller.post_touch_down(1160, 585, self.REEL_IN_CONTACT, 1).wait()
        return result.succeeded

    def stopReelIn(self, context: Context) -> bool:
        """
        停止收线动作
        """
        result = context.tasker.controller.post_touch_up(self.REEL_IN_CONTACT).wait()
        return result.succeeded

    def startBow(self, context: Context, direction: str) -> bool:
        """
        开始箭头转向动作
        """
        x = 150 if direction == "left" else 320
        y = 530
        result = context.tasker.controller.post_touch_down(x, y, self.BOWING_CONTACT, 1).wait()
        return result.succeeded

    def stopBow(self, context: Context) -> bool:
        """
        停止箭头转向动作
        """
        result = context.tasker.controller.post_touch_up(self.BOWING_CONTACT).wait()
        return result.succeeded
