# 开发指南

> 本文档提供项目架构、开发模式、测试方法的完整上下文，便于快速理解并正确实现功能。

---

## 项目概述

**MaaStarResonance** 是基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 的**星痕共鸣**（Blue Protocol: Star Resonance）游戏自动化工具。

- **语言**: Python >= 3.11
- **框架**: MaaFramework — 图像识别 + ADB 自动化
- **UI**: MFAAvalonia（独立前端，非本项目代码）
- **包管理**: uv
- **许可**: AGPL-3.0
- **运行方式**: 仅支持 MuMu 模拟器（Windows），通过 ADB 连接

---

## 目录结构

```
MaaStarResonance/
├── assets/
│   ├── interface.json          # 任务定义 & 用户选项配置（顶层入口）
│   └── resource/
│       └── base/
│           ├── pipeline/       # Pipeline JSON 文件（识别节点 & 动作链）
│           │   ├── general.json        # 通用节点（ESC、文字识别等）
│           │   ├── general/            # 通用功能（回主页面、省电模式等）
│           │   ├── fishing/            # 自动钓鱼相关
│           │   ├── little_games/       # 游星岛小游戏
│           │   ├── map/                # 地图传送/导航
│           │   ├── gathering/          # 简易采集
│           │   ├── cocoon/             # 刷茧
│           │   ├── daily/              # 日常任务
│           │   └── seson_center/       # 赛季中心
│           ├── image/          # 模板匹配用的 PNG 图片
│           └── model/          # OCR 模型
├── agent/
│   ├── main.py                 # Agent 入口（AgentServer 启动）
│   ├── module_loader.py        # 自动扫描加载 agent 下所有模块
│   ├── logger.py               # loguru 日志配置
│   ├── plugin_loader.py        # 插件加载器（扫描 agent/plugins/）
│   ├── plugin_registry.py      # 插件注册表（单例）
│   ├── custom/                 # 自定义动作（CustomAction 实现）
│   │   ├── general/            # 通用动作（聊天、回主页、切线等）
│   │   ├── little_games/       # 小游戏动作
│   │   └── *.py                # 各功能动作文件
│   ├── attach/                 # 参数读取工具（从 pipeline attach 节点取参）
│   ├── constant/               # 常量数据（按键码、地图点、鱼数据等）
│   ├── utils/                  # 工具函数（参数解析、模糊匹配等）
│   └── plugins/                # 侧载插件目录
├── scripts/                    # 构建/工具脚本
├── docs/                       # Docusaurus 文档站
└── pyproject.toml              # 项目配置（uv 管理）
```

---

## 核心架构：三层模型

MaaFramework 项目遵循 **Pipeline → CustomAction → Attach** 三层架构：

```
┌─────────────────────────────────────────────────────────┐
│  assets/interface.json                                  │
│  定义任务列表（task）、用户选项（option）、entry 名称      │
└──────────────────────┬──────────────────────────────────┘
                       │ entry 对应 pipeline 中的节点名
                       ▼
┌─────────────────────────────────────────────────────────┐
│  assets/resource/base/pipeline/*.json                   │
│  定义识别节点（recognition）和动作节点（action）           │
│  节点间通过 next 链接形成流水线                           │
│  动作为 Custom 类型时，委托给 Python 的 CustomAction       │
└──────────────────────┬──────────────────────────────────┘
                       │ custom_action 名称匹配
                       ▼
┌─────────────────────────────────────────────────────────┐
│  agent/custom/*.py                                      │
│  @AgentServer.custom_action("名称") 装饰的 Python 类      │
│  实现 run() 方法，接收 Context 和 RunArg                  │
│  通过 attach/*.py 的辅助函数读取 pipeline attach 参数      │
└─────────────────────────────────────────────────────────┘
```

### 关键概念

| 概念 | 说明 |
| ------ | ------ |
| **Pipeline Node** | JSON 中定义的节点，包含 recognition（识别）和/或 action（动作） |
| **entry** | interface.json 中 task 的入口节点名，对应 pipeline 中的 key |
| **next** | 节点执行后跳转的下一个节点（数组或字符串），支持 `[JumpBack]` 前缀 |
| **recognition** | 识别方式：TemplateMatch / OCR / ColorMatch / DirectHit / Custom |
| **action** | 动作类型：Click / ClickKey / LongPressKey / InputText / DoNothing / Custom |
| **attach** | pipeline 节点上的附加数据，用于向 CustomAction 传递参数 |
| **pipeline_override** | interface.json option 中对 pipeline 节点的覆盖，实现用户选项注入 |
| **CustomAction** | Python 侧实现的动作类，通过 `@AgentServer.custom_action("名称")` 注册 |
| **CustomRecognition** | Python 侧实现的识别类，通过 `@AgentServer.custom_recognition("名称")` 注册 |

---

## 数据流：参数传递

用户选项 → pipeline attach → CustomAction 的完整链路：

```
interface.json option (用户选择)
    │
    │ pipeline_override 覆盖 pipeline 节点的 attach 字段
    ▼
pipeline JSON 节点: "获取参数-XXX": { "action": "DoNothing", "attach": { "key": "value" } }
    │
    │ context.get_node_data("获取参数-XXX")["attach"]["key"]
    ▼
agent/attach/xxx_attach.py: get_xxx(context) 辅助函数读取
    │
    ▼
agent/custom/xxx_action.py: CustomAction.run() 中使用参数
```

### 参数传递的两种方式

**方式一：attach 节点（推荐用于选项类参数）**

```json
// pipeline JSON
"获取参数-需要切换的世界分线ID列表": {
    "action": "DoNothing",
    "attach": { "line_ids": "" }
}
```

```python
# attach/common_attach.py
def get_world_line_id_list(context: Context) -> list[str]:
    node = context.get_node_data("获取参数-需要切换的世界分线ID列表")
    line_ids = (node.get("attach", {}).get("line_ids", "")) if node else ""
    return str(line_ids).split(",") if line_ids else []
```

**方式二：custom_action_param（推荐用于数值/文本输入）**

```json
// interface.json option
"需要的最大成功钓鱼数量": {
    "type": "input",
    "pipeline_override": {
        "启动自动钓鱼入口": {
            "action": {
                "param": {
                    "custom_action_param": {
                        "max_success_fishing_count": "{最大成功钓鱼数量}"
                    }
                }
            }
        }
    }
}
```

```python
# custom/fishing_action.py
params = CustomActionParam(argv.custom_action_param)
max_count = int(params.data["max_success_fishing_count"])
```

---

## 调试工具

| 工具 | 用途 |
| ------ | ------ |
| **Maa Pipeline Support** (VSCode 插件) | Pipeline 调试、截图、ROI 获取、取色 |
| **MaaDebugger** | 独立调试工具 `python -m MaaDebugger` |
| **MFA Tools** | 截图、ROI、取色 |
| **check_resource.py** | 校验 pipeline 资源文件 `python scripts/check_resource.py <dir>` |

---

## 代码风格

- Python: 遵循现有代码风格，使用 loguru logger，type hints
- JSON: Prettier 格式化（pre-commit 自动执行）
- Markdown: markdownlint（pre-commit 自动执行）
- 图片: oxipng 无损压缩（pre-commit 自动执行）
- isort: 配置在 pyproject.toml 中

---

## 常用参考

- [MaaFramework 文档](https://maafw.xyz/docs)
- [M9A 开发者文档](https://1999.fan/zh_cn/develop/development.html) — 类似项目的最佳实践
- [Android KeyEvent 常量](https://developer.android.com/reference/android/view/KeyEvent)
- 项目内知识库: `docs/knowledge/` 目录
