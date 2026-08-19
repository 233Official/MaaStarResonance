# 如何添加新功能

> 本文档指导 AI 开发者如何为 MaaStarResonance 添加新的自动化功能。

---

## 功能开发流程总览

```
1. 截取游戏画面 → 确定识别区域 (ROI) 和模板图片
2. 编写 Pipeline JSON → 定义识别节点和动作节点
3. 编写 CustomAction (Python) → 实现复杂逻辑
4. 编写 Attach 辅助函数 → 读取用户配置参数
5. 注册到 interface.json → 定义任务入口和用户选项
6. 测试验证
```

---

## 步骤 1: 准备识别素材

### 截图与 ROI 获取

使用以下工具截取游戏画面并获取识别区域：

| 工具 | 用法 |
|------|------|
| **Maa Pipeline Support** (VSCode 插件) | 打开 pipeline JSON，点击节点可直接截图/框选 ROI |
| **MaaDebugger** | `python -m MaaDebugger`，连接模拟器后截图 |
| **MFA Tools** | 独立截图工具 |

### 模板图片

- 存放在 `assets/resource/base/image/` 对应子目录下
- PNG 格式，只保留需要匹配的关键区域（越小越精确）
- 使用 `green_mask: true` 过滤绿色背景（游戏 UI 常用）
- 分辨率基准：1280x720（MuMu 模拟器标准分辨率）

### OCR 模型

- 模型存放在 `assets/resource/base/model/` 和 `assets/MaaCommonAssets/OCR/`
- 默认使用 `ppocr_v5/zh_cn`，无需额外配置

---

## 步骤 2: 编写 Pipeline JSON

### 文件位置

在 `assets/resource/base/pipeline/` 下创建或编辑 JSON 文件：
- 简单功能直接放在 `pipeline/` 根目录（如 `roguelike.json`）
- 复杂功能建子目录（如 `pipeline/fishing/`、`pipeline/little_games/`）

### Pipeline 节点结构

每个节点是一个 JSON key-value 对，key 是节点名称，value 包含：

```json
{
    "节点名称": {
        "recognition": { ... },   // 可选：识别配置
        "action": { ... },        // 可选：动作配置
        "next": [ ... ],          // 可选：后继节点
        "attach": { ... },        // 可选：附加参数（供 CustomAction 读取）
        "pre_delay": 1000,        // 可选：执行前延迟(ms)
        "post_delay": 1000,       // 可选：执行后延迟(ms)
        "rate_limit": 8000,       // 可选：识别频率限制(ms)
        "timeout": 86400000       // 可选：超时时间(ms)
    }
}
```

### 识别类型 (recognition.type)

| 类型 | 说明 | 关键参数 |
|------|------|---------|
| `DirectHit` | 直接命中（无需识别，用于纯动作节点） | 无 |
| `TemplateMatch` | 模板匹配（找图片） | `template`, `roi`, `threshold`, `green_mask` |
| `OCR` | 文字识别 | `expected`, `roi`, `only_rec` |
| `ColorMatch` | 颜色匹配 | `lower`, `upper`, `roi`, `count`, `method` |
| `Custom` | 自定义识别（Python 实现） | `custom_recognition`, `custom_recognition_param` |

### 动作类型 (action.type)

| 类型 | 说明 | 关键参数 |
|------|------|---------|
| `DoNothing` | 不做任何操作（用于纯识别节点或参数节点） | 无 |
| `Click` | 点击 | `target` ([x,y,w,h] 或 true=点击识别位置) |
| `ClickKey` | 按键 | `key` (Android KeyEvent 键码) |
| `LongPressKey` | 长按按键 | `key`, `duration` (ms) |
| `InputText` | 输入文本 | `input_text` |
| `Custom` | 自定义动作（Python 实现） | `custom_action`, `custom_action_param` |

### 节点链接 (next)

```json
// 单个后继
"next": "下一个节点"

// 多个候选（按顺序尝试）
"next": ["节点A", "节点B"]

// JumpBack：执行完后跳回当前节点重新识别
"next": ["[JumpBack]从省电模式唤醒"]

// 带识别条件的跳转
"next": ["识别成功后的节点", "识别失败的备选节点"]
```

### 完整示例：一个简单的采集功能

```json
{
    "简易采集": {
        "action": {
            "type": "Custom",
            "param": {
                "custom_action": "SimpleGathering"
            }
        }
    },
    "获取参数-采集方案": {
        "action": "DoNothing",
        "attach": {
            "gather_type": "普通采集"
        }
    },
    "检测采集按钮": {
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": ["采集/采集按钮.png"],
                "roi": [500, 300, 100, 50],
                "green_mask": true
            }
        }
    },
    "点击采集按钮": {
        "recognition": {
            "type": "TemplateMatch",
            "param": {
                "template": ["采集/采集按钮.png"],
                "roi": [500, 300, 100, 50],
                "green_mask": true
            }
        },
        "action": "Click"
    }
}
```

---

## 步骤 3: 编写 CustomAction (Python)

### 文件位置

在 `agent/custom/` 下创建 Python 文件：
- 通用功能放 `agent/custom/general/`
- 小游戏放 `agent/custom/little_games/`
- 独立功能放 `agent/custom/` 根目录

### 基本模板

```python
from maa.agent.agent_server import AgentServer
from maa.context import Context, RecognitionDetail
from maa.custom_action import CustomAction

from agent.logger import logger
from agent.utils.param_utils import CustomActionParam, CustomActionParamError


@AgentServer.custom_action("MyFeature")
class MyFeatureAction(CustomAction):
    """我的新功能"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        """
        功能描述

        Args:
            context: 控制器上下文
            argv: 运行参数
                - my_param: 参数说明

        Returns:
            执行结果：True / False
        """
        try:
            # 1. 解析参数
            params = CustomActionParam(argv.custom_action_param)
            my_param = params.data.get("my_param", "default_value")

            # 2. 截图
            img = context.tasker.controller.post_screencap().wait().get()

            # 3. 识别
            result: RecognitionDetail | None = context.run_recognition(
                "检测某按钮", img
            )

            if result and result.hit:
                # 4. 执行动作
                context.run_action("点击某按钮")
                logger.info("操作成功")
                return True
            else:
                logger.warning("未识别到目标")
                return False

        except CustomActionParamError as exc:
            logger.error(f"参数错误: {exc}")
            return False
        except Exception as exc:
            logger.exception(f"执行失败: {exc}")
            return False
```

### 常用 Context API

```python
# 截图
img = context.tasker.controller.post_screencap().wait().get()

# 运行识别（返回 RecognitionDetail | None）
result = context.run_recognition("节点名", img)

# 运行识别（带 pipeline_override）
result = context.run_recognition(
    "通用文字识别", img,
    pipeline_override={
        "通用文字识别": {"expected": "目标文字", "roi": [x, y, w, h]}
    }
)

# 运行动作（运行 pipeline 中定义的 action 节点）
context.run_action("动作节点名")

# 运行任务（运行 pipeline 中定义的完整节点链）
context.run_task(entry="入口节点名")

# 运行任务（带 pipeline_override）
context.run_task(
    entry="节点名",
    pipeline_override={"节点名": {"action": {"param": {...}}}}
)

# 直接控制
context.tasker.controller.post_click(x, y).wait()           # 点击坐标
context.tasker.controller.post_click_key(key_code).wait()    # 按键
context.tasker.controller.post_touch_down(x, y, contact, pressure).wait()  # 按下
context.tasker.controller.post_touch_up(contact).wait()      # 抬起
context.tasker.controller.post_input_text("文本").wait()     # 输入文本

# 检查任务是否被用户停止
if context.tasker.stopping:
    return False

# 获取节点 attach 数据
node_data = context.get_node_data("节点名")  # 返回 dict | None
attach_value = node_data.get("attach", {}).get("key", "default")

# 覆盖后续节点
context.override_next("当前节点名", ["下一个节点名"])
```

### 按键码

按键码定义在 `agent/constant/key_event/AndroidKeyEvent.json` 中，通过 `ANDROID_KEY_EVENT_DATA` 访问：

```python
from agent.constant.key_event import ANDROID_KEY_EVENT_DATA

key_code = ANDROID_KEY_EVENT_DATA["KEYCODE_ESCAPE"]  # 111
key_code = ANDROID_KEY_EVENT_DATA["KEYCODE_W"]       # 51
key_code = ANDROID_KEY_EVENT_DATA["KEYCODE_E"]       # 33
key_code = ANDROID_KEY_EVENT_DATA["KEYCODE_F"]       # 34
```

---

## 步骤 4: 编写 Attach 辅助函数

### 文件位置

在 `agent/attach/` 下创建或编辑文件，文件名与功能对应（如 `my_feature_attach.py`）。

### 装饰器方式（推荐）

项目提供了 `@attach_param` 和 `@attach_param_list` 装饰器，消除重复的模板代码：

```python
from maa.context import Context
from agent.attach import attach_param, attach_param_list


@attach_param("获取参数-我的参数", "my_key", "默认值")
def get_my_param(context: Context) -> str:
    """获取我的参数"""
    ...


@attach_param("获取参数-我的数值", "my_number", 0, int)
def get_my_number(context: Context) -> int:
    """获取我的数值参数"""
    ...


@attach_param("获取参数-是否开启", "enabled", True, bool)
def get_is_enabled(context: Context) -> bool:
    """获取是否开启参数"""
    ...


@attach_param_list("获取参数-ID列表", "line_ids")
def get_id_list(context: Context) -> list[str]:
    """获取ID列表参数（逗号分隔，如 "1,201,302"）"""
    ...
```

**装饰器参数说明**：

| 参数 | 说明 |
|------|------|
| 第1个 | pipeline 节点名（与 pipeline JSON 中的 key 一致） |
| 第2个 | attach 字典中的键名（snake_case 英文） |
| 第3个 | 默认值（节点不存在时的 fallback） |
| 第4个 | 类型转换函数（`str`/`int`/`bool`），可省略（默认 `str`） |

**`@attach_param_list` 专用于逗号分隔的列表参数**，自动做 `split(",")` 处理。

### 手动方式（仅用于动态节点名）

当节点名需要动态拼接时（如 `f"获取参数-需要购买的{type_str}配件"`），无法使用装饰器，需手动编写：

```python
from maa.context import Context
from agent.logger import logger


def get_fish_equipment(context: Context, type_str: str) -> str:
    """获取钓鱼配件参数（动态节点名，无法用装饰器）"""
    node = context.get_node_data(f"获取参数-需要购买的{type_str}配件")
    value = (node.get("attach", {}).get("item_name", f"普通{type_str}")) if node else f"普通{type_str}"
    logger.info("需要购买的{}: {}", type_str, value)
    return str(value)
```

**命名规范**：
- pipeline 节点名：`获取参数-参数描述`
- attach key：使用 snake_case 英文
- 函数名：`get_` + 参数名（snake_case）

---

## 步骤 5: 注册到 interface.json

### 添加任务 (task)

在 `assets/interface.json` 的 `task` 数组中添加：

```json
{
    "name": "我的新功能",
    "entry": "我的新功能入口",
    "description": "功能描述文本",
    "option": [
        "我的选项1",
        "我的选项2"
    ]
}
```

- `name`: 显示在 UI 上的任务名称
- `entry`: 对应 pipeline JSON 中的节点 key
- `description`: 任务描述（可选）
- `option`: 引用的 option 名称列表（可选）

### 添加选项 (option)

在 `assets/interface.json` 的 `option` 对象中添加：

**选择类型 (select)**：

```json
"我的选项1": {
    "type": "select",
    "default_case": "默认值",
    "description": "选项说明",
    "cases": [
        {
            "name": "选项A",
            "pipeline_override": {
                "获取参数-我的参数": {
                    "attach": {
                        "my_key": "value_a"
                    }
                }
            }
        },
        {
            "name": "选项B",
            "pipeline_override": {
                "获取参数-我的参数": {
                    "attach": {
                        "my_key": "value_b"
                    }
                }
            }
        }
    ]
}
```

**输入类型 (input)**：

```json
"我的选项2": {
    "type": "input",
    "inputs": [
        {
            "name": "输入框标签",
            "description": "输入说明",
            "pipeline_type": "int",
            "default": "0"
        }
    ],
    "pipeline_override": {
        "我的新功能入口": {
            "action": {
                "param": {
                    "custom_action_param": {
                        "my_number": "{输入框标签}"
                    }
                }
            }
        }
    }
}
```

**选项嵌套**：select 的 case 可以通过 `option` 字段引用其他 option，实现级联选项：

```json
{
    "name": "世界",
    "option": ["需要发送消息的世界频道分线ID"],
    "pipeline_override": { ... }
}
```

---

## 步骤 6: 添加常量数据（如需要）

如果功能需要常量数据（如物品列表、地图坐标等），在 `agent/constant/` 下创建：

```
agent/constant/my_feature/
├── __init__.py      # from .MyData import MY_DATA
└── MyData.json      # JSON 数据文件
```

```python
# agent/constant/my_feature/__init__.py
import json
from pathlib import Path

_data_path = Path(__file__).parent / "MyData.json"
with open(_data_path, encoding="utf-8") as f:
    MY_DATA = json.load(f)
```

---

## 检查清单

完成功能开发后，确认以下各项：

- [ ] Pipeline JSON 语法正确，节点间链接完整
- [ ] 模板图片已放入 `assets/resource/base/image/` 对应目录
- [ ] CustomAction 已用 `@AgentServer.custom_action("名称")` 注册
- [ ] `custom_action` 名称与 pipeline 中引用的名称一致
- [ ] Attach 辅助函数已创建，能正确读取参数
- [ ] interface.json 中已添加 task 和 option
- [ ] entry 名称与 pipeline 中的节点 key 一致
- [ ] `pre-commit run --all-files` 通过
- [ ] `python scripts/check_resource.py assets/resource/base` 通过
