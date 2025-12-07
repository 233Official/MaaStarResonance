# 定义一些页面相关常量
from enum import Enum
from typing import Optional, List

import numpy

from maa.context import Context


class GamePageEnum(Enum):
    GAMEPLAY_COMPENSATION_SHOP = "玩法补偿商店"
    ACTIVITY_COMPENSATION_SHOP = "活跃补偿商店"


# 枚举 -> Pipeline 节点名 的映射表
PAGE_NODE_MAP: dict[GamePageEnum, str] = {
    GamePageEnum.GAMEPLAY_COMPENSATION_SHOP: "RecognizeGameplayCompensationShop",
    GamePageEnum.ACTIVITY_COMPENSATION_SHOP: "RecognizeActivityCompensationShop",
}


class PageRecognizer:
    def __init__(self, node_map: dict[GamePageEnum, str]):
        self._node_map = node_map

    def recognize_current_page(
        self,
        context: Context,
        image: numpy.ndarray,
        candidates: List[GamePageEnum],
        pipeline_override: dict | None = None,
        node_map: dict[GamePageEnum, str] | None = None,
    ) -> Optional[GamePageEnum]:
        """
        按顺序识别图像中的页面，返回第一个识别成功的 GamePageEnum。

        Args:
            context: MaaFramework Context 对象
            image: 待识别的截图 (numpy.ndarray)
            candidates: 按优先级排序的候选页面列表
            pipeline_override: 可选的 pipeline 覆盖配置
            node_map: 枚举到节点名的映射，默认使用 PAGE_NODE_MAP

        Returns:
            第一个识别成功的 GamePageEnum，全部失败返回 None
        """
        if pipeline_override is None:
            pipeline_override = {}
        if node_map is None:
            node_map = PAGE_NODE_MAP

        for page in candidates:
            node_name = node_map.get(page)
            if node_name is None:
                # 未配置映射，跳过并警告
                print(f"[Warning] 页面 {page} 未配置 Pipeline 节点映射，已跳过")
                continue

            reco_detail = context.run_recognition(node_name, image, pipeline_override)

            if reco_detail and reco_detail.hit:
                return page

        return None
