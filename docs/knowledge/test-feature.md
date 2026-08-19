# 如何测试功能

> 本文档介绍 MaaStarResonance 的测试方法，包括 VSCode 插件调试、脚本化测试、以及手动验证流程。

---

## 测试方式总览

| 方式 | 适用场景 | 工具 |
|------|---------|------|
| **VSCode Maa 插件调试** | Pipeline 节点调试、识别验证、ROI 调整 | Maa Pipeline Support |
| **资源校验脚本** | Pipeline JSON 语法和资源完整性检查 | check_resource.py |
| **MaaDebugger** | 独立调试、截图分析、节点测试 | MaaDebugger |
| **手动运行验证** | 端到端功能测试 | MFAAvalonia UI |
| **Python 单元测试** | CustomAction 逻辑测试（需 mock） | pytest（待建设） |

---

## 方式一：VSCode Maa Pipeline Support 插件（推荐）

这是项目**最主要的调试方式**，VSCode 插件 `nekosu.maa-support` 提供了 Pipeline 的可视化调试能力。

### 安装

在 VSCode 扩展市场搜索 `maa-support` 或访问：
https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support

### 配置

插件需要配置 MaaFramework 的路径。在项目根目录创建 `.maafw/` 目录（插件会自动检测）：

```json
// .maafw/config.json（插件自动生成或手动创建）
{
    "resource": "assets/resource/base",
    "controller": "adb"
}
```

### 调试 Pipeline 节点

1. **打开任意 pipeline JSON 文件**（如 `assets/resource/base/pipeline/fishing/main_action.json`）
2. 插件会自动解析 JSON 中的节点
3. 点击节点名称旁边的 **调试图标**（或右键选择调试）
4. 插件会连接模拟器，截取当前画面，运行该节点的 recognition
5. 显示识别结果：是否命中、识别框位置、匹配置信度

### 截图与 ROI 获取

1. 使用插件的截图功能获取模拟器当前画面
2. 在截图上框选需要识别的区域
3. 插件自动生成 ROI 坐标 `[x, y, width, height]`
4. 直接粘贴到 pipeline JSON 的 `roi` 字段

### 取色

1. 使用插件的取色功能
2. 在截图上点击需要匹配的颜色
3. 插件自动生成 HSV 颜色范围 `lower` 和 `upper`
4. 用于 `ColorMatch` 类型的 recognition

### 调试验证流程

```
编写/修改 pipeline 节点
    ↓
VSCode 插件调试该节点
    ↓
确认识别命中、ROI 正确、置信度足够
    ↓
调试动作节点确认点击位置正确
    ↓
手动运行完整任务验证端到端流程
```

---

## 方式二：资源校验脚本

项目提供了 `scripts/check_resource.py` 用于校验 pipeline 资源文件的完整性和语法正确性。

### 使用方法

```bash
# 校验整个资源目录
python scripts/check_resource.py assets/resource/base

# 校验多个目录
python scripts/check_resource.py assets/resource/base assets/resource/jp
```

### 校验内容

- Pipeline JSON 语法是否正确
- 引用的模板图片文件是否存在
- 引用的 OCR 模型是否存在
- 节点间的 `next` 引用是否指向存在的节点
- `custom_action` / `custom_recognition` 名称是否与 Python 代码匹配

**注意**：此脚本只校验资源文件的静态完整性，不运行实际的图像识别。

---

## 方式三：MaaDebugger 独立调试

MaaDebugger 是一个独立的调试工具，可以不依赖 VSCode 使用。

### 安装与启动

```bash
pip install MaaDebugger
python -m MaaDebugger
# 指定端口
python -m MaaDebugger --port 8080
```

### 使用

1. 启动 MaaDebugger
2. 连接模拟器（ADB）
3. 加载项目的 resource 目录
4. 可以逐节点调试 pipeline
5. 查看识别结果、截图、日志

---

## 方式四：手动运行验证（端到端测试）

### 前置条件

1. MuMu 模拟器已启动，星痕共鸣已安装
2. ADB 连接正常
3. 项目依赖已安装 (`uv sync`)
4. MaaFramework 已放入 `deps/` 目录

### 运行步骤

```bash
# 方式1: 通过 MFAAvalonia UI（用户正常使用的方式）
# 启动 MFAAvalonia，加载 assets/interface.json，选择任务运行

# 方式2: 直接运行 agent（开发者调试）
# 需要先启动 MFAAvalonia，它会通过 AgentServer 与 agent/main.py 通信
```

### 验证要点

1. **日志检查**：观察 `agent/logger.py` 输出的日志，确认参数读取正确、识别命中、动作执行
2. **识别验证**：确认识别节点能正确命中目标
3. **动作验证**：确认点击/按键位置正确
4. **流程验证**：确认整个任务流程能正常完成
5. **边界情况**：测试异常处理（掉线、弹窗、超时等）

---

## 方式五：脚本化测试（可行性分析）

### 当前状态

项目目前没有完整的自动化测试体系。以下是可行性分析：

### 可行的脚本化测试

**1. Pipeline JSON 语法校验（已有）**

```bash
python scripts/check_resource.py assets/resource/base
```

**2. CustomAction 参数解析测试**

可以为 `CustomActionParam` 等工具类编写单元测试：

```python
# tests/test_param_utils.py
import pytest
from agent.utils.param_utils import CustomActionParam, CustomActionParamError

def test_valid_param():
    param = CustomActionParam('{"key": "value"}')
    assert param.data["key"] == "value"

def test_empty_param():
    with pytest.raises(CustomActionParamError):
        CustomActionParam("")

def test_invalid_json():
    with pytest.raises(CustomActionParamError):
        CustomActionParam("not json")

def test_require_keys():
    param = CustomActionParam('{"a": 1, "b": 2}')
    result = param.require(["a", "b"])
    assert result == {"a": 1, "b": 2}

def test_require_missing():
    param = CustomActionParam('{"a": 1}')
    with pytest.raises(CustomActionParamError):
        param.require(["a", "b"])
```

**3. Attach 函数测试（需 mock Context）**

```python
# tests/test_attach.py
from unittest.mock import MagicMock
from agent.attach.common_attach import get_login_timeout

def test_get_login_timeout():
    context = MagicMock()
    context.get_node_data.return_value = {
        "attach": {"login_timeout": 240}
    }
    assert get_login_timeout(context) == 240

def test_get_login_timeout_default():
    context = MagicMock()
    context.get_node_data.return_value = None
    assert get_login_timeout(context) == 300
```

**4. Pipeline 节点结构校验（可扩展）**

可以编写脚本检查 pipeline JSON 的额外约束：

```python
# scripts/validate_pipeline.py
"""自定义 pipeline 校验脚本"""
import json
from pathlib import Path

def check_node_names(pipeline_dir: Path):
    """检查节点命名规范"""
    for json_file in pipeline_dir.rglob("*.json"):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        for node_name in data:
            # 检查命名规范
            if node_name.startswith("获取参数-"):
                assert "attach" in data[node_name], f"{json_file}: {node_name} 缺少 attach"
            # ... 更多检查
```

### 不可完全脚本化的部分

以下部分**必须依赖实际游戏画面**，无法完全脚本化：

- **图像识别准确性**：模板匹配的置信度、OCR 识别率需要在实际游戏画面上验证
- **坐标点击精度**：不同分辨率、不同 UI 状态下点击位置可能偏移
- **时序和延迟**：游戏加载时间、动画效果影响自动化流程
- **异常处理**：掉线、弹窗、服务器维护等无法预测的场景

### 建议的测试策略

```
开发阶段：
  VSCode 插件调试单个节点 ←→ 修改 pipeline/代码
  
提交前：
  1. python scripts/check_resource.py assets/resource/base
  2. pre-commit run --all-files
  3. 手动运行关键功能验证
  
发布前：
  完整跑一遍所有功能，确认无回归
```

---

## 调试技巧

### 1. 日志调试

项目使用 loguru，日志级别为 DEBUG。关键日志：

```python
logger.info("参数值: {}", value)       # 参数读取
logger.info("识别结果: {}", result.hit) # 识别命中
logger.warning("异常情况")              # 异常
logger.error("错误信息")                # 错误
```

### 2. 识别调试

在 CustomAction 中临时添加调试代码：

```python
# 保存截图用于离线分析
import cv2
img = context.tasker.controller.post_screencap().wait().get()
cv2.imwrite("debug_screenshot.png", img)

# 打印识别详情
result = context.run_recognition("节点名", img)
if result:
    logger.debug(f"hit: {result.hit}, box: {result.box}")
    if result.best_result:
        logger.debug(f"best: {result.best_result.text}, score: {result.best_result.score}")
    if result.all_results:
        for r in result.all_results:
            logger.debug(f"  all: {r.text}, score: {r.score}")
```

### 3. Pipeline 调试

在 pipeline JSON 中临时添加调试节点：

```json
"调试截图": {
    "recognition": "DirectHit",
    "action": {
        "type": "Custom",
        "param": {
            "custom_action": "debug_screenshot"
        }
    }
}
```

### 4. 通用文字识别节点

项目提供了 `通用文字识别` 节点，可以通过 `pipeline_override` 动态指定识别内容：

```python
result = context.run_recognition(
    "通用文字识别",
    img,
    pipeline_override={
        "通用文字识别": {
            "expected": "目标文字",
            "roi": [x, y, w, h]
        }
    }
)
```

---

## 常见问题

### Q: 识别不到目标怎么办？

1. 检查 ROI 是否正确（用 VSCode 插件截图验证）
2. 检查模板图片是否清晰、是否包含足够特征
3. 尝试调整 `threshold`（降低阈值，如 0.7 → 0.6）
4. 尝试添加 `green_mask: true` 过滤背景
5. 对于 OCR，检查 `expected` 文字是否与实际显示一致

### Q: 点击位置偏移怎么办？

1. 确认模拟器分辨率是 1280x720
2. 使用 `"target": true` 点击识别到的位置而非固定坐标
3. 检查 ROI 是否包含了正确的可点击区域

### Q: 任务运行中断了怎么办？

1. 检查日志中是否有 `context.tasker.stopping` 相关输出
2. 确认是否有超时设置过短
3. 检查是否有未处理的异常导致 return False

### Q: 如何调试循环任务？

循环任务（如 `挂机自动批复入队申请`）使用 `next` 指向自身实现循环。调试时：
1. 先单独调试循环体内的识别节点
2. 确认识别能命中后，再调试完整循环
3. 注意 `rate_limit` 和 `timeout` 的设置
