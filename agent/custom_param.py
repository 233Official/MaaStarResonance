"""custom_action_param 解析工具。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


class CustomActionParamError(ValueError):
    """在解析或校验 custom_action_param 时抛出的异常。"""


class CustomActionParam:
    """解析并校验 MaaFW custom_action_param 的辅助类。"""

    def __init__(self, raw: str) -> None:
        """初始化解析器并解析 JSON 字符串。

        Args:
            raw: `custom_action_param` 字符串。

        Raises:
            CustomActionParamError: 当入参为空、非法或不是 JSON 对象时抛出。
        """

        self._data = self._load_json(raw)

    @staticmethod
    def _load_json(raw: str) -> dict[str, Any]:
        if not raw:
            raise CustomActionParamError("custom_action_param 不能为空")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - 抛错路径
            raise CustomActionParamError("custom_action_param 不是合法的 JSON") from exc
        if not isinstance(data, dict):
            raise CustomActionParamError("custom_action_param 必须是 JSON 对象")
        return data

    @property
    def data(self) -> dict[str, Any]:
        """返回解析后的完整数据。"""

        return self._data

    def require(self, keys: Iterable[str]) -> dict[str, Any]:
        """校验必填字段并返回对应键值。

        Args:
            keys: 需要存在且非空的字段列表。

        Raises:
            CustomActionParamError: 当缺少任意必填字段时抛出。

        Returns:
            包含指定字段的字典副本。
        """

        result: dict[str, Any] = {}
        missing: list[str] = []
        for key in keys:
            value = self._data.get(key)
            if value:
                result[key] = value
            else:
                missing.append(key)
        if missing:
            joined = ", ".join(missing)
            raise CustomActionParamError(f"缺少必要字段: {joined}")
        return result
