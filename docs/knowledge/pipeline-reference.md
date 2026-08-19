# Pipeline 参考手册

> MaaFramework Pipeline 语法快速参考，供 AI 开发时查阅。

---

## Pipeline 节点完整字段

```json
{
    "节点名称": {
        "recognition": {
            "type": "识别类型",
            "param": { ... }
        },
        "action": {
            "type": "动作类型",
            "param": { ... }
        },
        "next": ["后继节点"],
        "attach": { "key": "value" },
        "pre_delay": 0,
        "post_delay": 0,
        "rate_limit": 1000,
        "timeout": 20000,
        "enabled": true,
        "inverse": false,
        "focus": "提示信息"
    }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `recognition` | object | 否 | 识别配置，不填默认 DirectHit |
| `action` | object | 否 | 动作配置，不填默认 DoNothing |
| `next` | string\|array | 否 | 后继节点，支持 `[JumpBack]` 前缀 |
| `attach` | object | 否 | 附加数据，供 CustomAction 通过 `context.get_node_data()` 读取 |
| `pre_delay` | int | 否 | 执行前延迟（毫秒），默认 0 |
| `post_delay` | int | 否 | 执行后延迟（毫秒），默认 0 |
| `rate_limit` | int | 否 | 识别频率限制（毫秒），防止过快轮询 |
| `timeout` | int | 否 | 节点超时时间（毫秒），默认 20000 |
| `enabled` | bool | 否 | 是否启用，默认 true，可通过 pipeline_override 控制 |
| `inverse` | bool | 否 | 识别结果取反（识别不到才算命中），默认 false |
| `focus` | string | 否 | 提示信息，识别失败时显示 |

---

## 识别类型详解

### DirectHit — 直接命中

不做任何识别，直接命中。用于纯动作节点。

```json
"ESC": {
    "recognition": "DirectHit",
    "action": {
        "type": "ClickKey",
        "param": { "key": 111 }
    }
}
```

### TemplateMatch — 模板匹配

在屏幕上查找模板图片。

```json
"检测主页面": {
    "recognition": {
        "type": "TemplateMatch",
        "param": {
            "template": ["general/主页面任务图标.png"],
            "roi": [22, 218, 26, 23],
            "threshold": 0.7,
            "green_mask": true,
            "method": 5
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `template` | string\|array | 模板图片路径（相对于 image/ 目录），多个模板任一匹配 |
| `roi` | [x,y,w,h] | 识别区域，[0,0,0,0] 表示全屏 |
| `threshold` | float | 匹配阈值 0-1，默认 0.7，越高越严格 |
| `green_mask` | bool | 绿色掩码，过滤模板中的绿色背景 |
| `method` | int | 匹配算法，1/3/5（TM_SQDIFF/CCOEFF/CCORR），默认 5 |

### OCR — 文字识别

识别屏幕上的文字。

```json
"检测确认按钮": {
    "recognition": {
        "type": "OCR",
        "param": {
            "expected": ["确认"],
            "roi": [767, 517, 59, 27],
            "only_rec": false,
            "replace": ["己", "已"]
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `expected` | string\|array | 期望的文字，支持正则表达式 |
| `roi` | [x,y,w,h] | 识别区域 |
| `only_rec` | bool | 仅识别不筛选，返回所有识别到的文字 |
| `replace` | array | 文字替换对，用于纠正常见 OCR 错误 |

### ColorMatch — 颜色匹配

匹配指定区域的颜色。

```json
"检测鱼鱼咬钩": {
    "recognition": {
        "type": "ColorMatch",
        "param": {
            "lower": [12, 250, 207],
            "upper": [24, 255, 255],
            "roi": [620, 357, 34, 32],
            "count": 8,
            "method": 40,
            "connected": false
        }
    }
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `lower` | [H,S,V] | HSV 下限 |
| `upper` | [H,S,V] | HSV 上限 |
| `roi` | [x,y,w,h] | 识别区域 |
| `count` | int | 最少匹配像素数 |
| `method` | int | 匹配方法（4=RGB, 40=HSV, 6=GRAY 等） |
| `connected` | bool | 是否要求连通区域 |

### Custom — 自定义识别

使用 Python 实现的自定义识别。

```json
"复合识别": {
    "recognition": {
        "type": "Custom",
        "param": {
            "custom_recognition": "AllMatch",
            "custom_recognition_param": {
                "nodes": ["节点A", "节点B"]
            }
        }
    }
}
```

---

## 动作类型详解

### DoNothing — 不做操作

```json
"参数节点": {
    "action": "DoNothing",
    "attach": { "key": "value" }
}
```

### Click — 点击

```json
// 固定坐标点击 [x, y, w, h]（在区域内随机点击）
"点击按钮": {
    "action": {
        "type": "Click",
        "param": {
            "target": [640, 360, 10, 10]
        }
    }
}

// 点击识别到的位置
"点击识别目标": {
    "recognition": { ... },
    "action": {
        "type": "Click",
        "param": {
            "target": true
        }
    }
}

// 点击偏移位置（识别位置 + 偏移量）
"点击偏移位置": {
    "recognition": { ... },
    "action": {
        "type": "Click",
        "param": {
            "target": true,
            "target_offset": [10, 20, 0, 0]
        }
    }
}
```

### ClickKey — 按键

```json
"按ESC": {
    "action": {
        "type": "ClickKey",
        "param": {
            "key": 111
        }
    }
}
```

### LongPressKey — 长按按键

```json
"按住W键1秒": {
    "action": {
        "type": "LongPressKey",
        "param": {
            "key": 51,
            "duration": 1000
        }
    }
}
```

### InputText — 输入文本

```json
"输入文本": {
    "action": {
        "type": "InputText",
        "param": {
            "input_text": "要输入的内容"
        }
    }
}
```

### Custom — 自定义动作

```json
"执行我的功能": {
    "action": {
        "type": "Custom",
        "param": {
            "custom_action": "MyFeature",
            "custom_action_param": {
                "key1": "value1",
                "key2": 123
            }
        }
    }
}
```

### Swipe — 滑动

```json
"滑动屏幕": {
    "action": {
        "type": "Swipe",
        "param": {
            "begin": [640, 500],
            "end": [640, 200],
            "duration": 500
        }
    }
}
```

---

## next 跳转规则

```json
// 顺序执行：A → B → C
"A": { "next": "B" },
"B": { "next": "C" },
"C": { }

// 分支：A 识别成功走 B，失败走 C
"A": {
    "recognition": { ... },
    "next": ["B", "C"]    // 识别成功走 B，识别失败走 C
}

// JumpBack：执行 B 后跳回 A 重新识别
"A": {
    "next": ["[JumpBack]B"]
},
"B": {
    "action": { ... }
    // 执行完后回到 A
}

// 循环：A → B → A（死循环，直到 timeout）
"A": { "next": "B", "timeout": 86400000 },
"B": { "next": "A" }
```

---

## interface.json 结构

```json
{
    "interface_version": 2,
    "name": "项目名",
    "version": "v0.12.0",
    "title": "显示标题",
    "controller": [
        { "name": "模拟器", "type": "Adb" }
    ],
    "resource": [
        { "name": "国服", "path": ["./resource/base"] }
    ],
    "agent": {
        "child_exec": "{PROJECT_DIR}/../.venv/Scripts/python.exe",
        "child_args": ["{PROJECT_DIR}/../agent/main.py"]
    },
    "task": [
        {
            "name": "任务显示名",
            "entry": "pipeline入口节点名",
            "description": "任务描述",
            "option": ["选项名1", "选项名2"]
        }
    ],
    "option": {
        "选项名1": {
            "type": "select",
            "default_case": "默认选中项",
            "description": "选项描述",
            "cases": [
                {
                    "name": "选项A",
                    "option": ["级联选项名"],
                    "pipeline_override": {
                        "节点名": {
                            "attach": { "key": "value" },
                            "enabled": true
                        }
                    }
                }
            ]
        },
        "选项名2": {
            "type": "input",
            "inputs": [
                {
                    "name": "输入框名",
                    "description": "输入说明",
                    "pipeline_type": "int",
                    "default": "0"
                }
            ],
            "pipeline_override": {
                "节点名": {
                    "action": {
                        "param": {
                            "custom_action_param": {
                                "key": "{输入框名}"
                            }
                        }
                    }
                }
            }
        }
    }
}
```

---

## 常用 pipeline_override 模式

### 覆盖 attach 参数

```json
"pipeline_override": {
    "获取参数-XXX": {
        "attach": { "key": "新值" }
    }
}
```

### 覆盖 custom_action_param

```json
"pipeline_override": {
    "入口节点": {
        "action": {
            "param": {
                "custom_action_param": {
                    "key": "{用户输入占位符}"
                }
            }
        }
    }
}
```

### 启用/禁用节点

```json
"pipeline_override": {
    "专注采集": { "enabled": true },
    "普通采集": { "enabled": false }
}
```

### 覆盖识别参数

```json
"pipeline_override": {
    "通用文字识别": {
        "expected": "新文字",
        "roi": [x, y, w, h]
    }
}
```

---

## 项目中的通用节点

以下节点在多个功能中复用，可以直接在 pipeline 或 Python 代码中引用：

| 节点名 | 类型 | 说明 |
|--------|------|------|
| `通用文字识别` | OCR | 通用 OCR，配合 pipeline_override 使用 |
| `图片识别是否在主页面` | TemplateMatch | 检测是否在游戏主页面 |
| `回到主页面` | Custom | 调用 return_main_page 返回主页 |
| `关闭所有弹窗广告` | Custom | 调用 CloseAd 关闭广告 |
| `ESC` | ClickKey | 按 ESC 键（key=111） |
| `按住W键1秒` | LongPressKey | 按住 W 键 1 秒 |
| `E-冲刺` | ClickKey | 按 E 键（key=33） |
| `循环F` | ClickKey | 循环按 F 键 |
| `启动指定APP` | Custom | 启动星痕共鸣 APP |
| `关闭指定APP` | Custom | 关闭星痕共鸣 APP |
| `重启指定APP` | Custom | 重启星痕共鸣 APP |
| `重启并登录星痕共鸣` | Custom | 重启并登录游戏 |
| `切换分线` | Custom | 切换世界分线 |
| `聊天频道发言` | Custom | 发送聊天消息 |
| `周期性聊天频道发言` | Custom | 循环发送聊天消息 |

---

## 常用 CustomAction 列表

| 注册名 | 文件 | 说明 |
|--------|------|------|
| `AutoFishing` | custom/fishing_action.py | 自动钓鱼 |
| `SendMessage` | custom/general/chat_message.py | 发送聊天消息 |
| `SendMessageLoop` | custom/general/chat_message.py | 循环发送聊天消息 |
| `SwitchLine` | custom/general/world_line_switcher.py | 切换分线 |
| `CloseAd` | custom/general/ad_close.py | 关闭广告弹窗 |
| `return_main_page` | custom/general/general.py | 返回主页面 |
| `run_pipeline_node` | custom/common_action.py | 运行指定 pipeline 节点 |
| `decision_router` | custom/common_action.py | 条件分支路由 |
| `wait_x_seconds` | custom/common_action.py | 等待指定秒数 |
| `run_custom_actions_series` | custom/common_action.py | 运行一系列动作 |
| `move_wsad` | custom/common_action.py | WSAD 移动 |
| `RestartAndLoginXHGM` | custom/app_manage_action.py | 重启并登录游戏 |
| `StartTargetApp` | custom/app_manage_action.py | 启动 APP |
| `StopTargetApp` | custom/app_manage_action.py | 关闭 APP |

---

## 常用 CustomRecognition 列表

| 注册名 | 文件 | 说明 |
|--------|------|------|
| `AllMatch` | custom/general/general.py | 所有指定节点都识别成功才算成功 |
| `AnyMatch` | custom/general/general.py | 任一指定节点识别成功即返回 |

---

## 分辨率与坐标系

- **基准分辨率**: 1280 x 720（MuMu 模拟器标准分辨率）
- **坐标原点**: 左上角 (0, 0)
- **ROI 格式**: `[x, y, width, height]`（左上角坐标 + 宽高）
- **全屏 ROI**: `[0, 0, 0, 0]` 或 `[0, 0, 1280, 720]`

---

## Android KeyEvent 常用键码

| 键名 | 键码 | 说明 |
|------|------|------|
| KEYCODE_ESCAPE | 111 | ESC |
| KEYCODE_W | 51 | W |
| KEYCODE_A | 29 | A |
| KEYCODE_S | 47 | S |
| KEYCODE_D | 32 | D |
| KEYCODE_E | 33 | E |
| KEYCODE_F | 34 | F |
| KEYCODE_I | 37 | I |
| KEYCODE_Z | 54 | Z |
| KEYCODE_ENTER | 66 | Enter |
| KEYCODE_BACK | 4 | 返回键 |

完整键码表见 `agent/constant/key_event/AndroidKeyEvent.json`。
