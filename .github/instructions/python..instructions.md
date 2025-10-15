---
description: Python 项目通用编码规范
applyTo: " **/*.py, src/**/*.py, tests/**/*.py"
---

# Python 项目编码规范

## 项目结构

- 使用 src 布局，如 `src/your_package_name/`
- 测试代码放在与 `src/` 平行的 `tests/` 目录
- 配置文件放在 `config/` 或使用环境变量, 如果配置比较少可以放在 `config.toml` 里
- 使用 uv 管理项目依赖, 相应的依赖项存储在 `pyproject.toml`, python 版本要求 >=3.11
- 静态文件放在 `static/` 目录

## 代码风格

- 使用 Black 进行代码格式化
- 使用 isort 排序导入
- 遵循 PEP 8 命名规范：
  - 函数和变量使用 snake_case
  - 类使用 PascalCase
  - 常量使用 UPPER_CASE
- 最大行长度为 88 个字符（Black 默认）
- 优先使用绝对导入
- 始终优先考虑代码可读性和清晰性。
- 为每个函数编写清晰简明的注释。
- 确保函数命名具有描述性，并包含类型提示。
- 保持正确缩进（每级缩进使用 4 个空格）。

---

## 常用库

- 使用 httpx 进行 HTTP 请求
- 使用 pydantic 进行数据验证和设置管理
- 使用 loguru 进行日志记录
- 使用 pathlib 进行文件和路径操作
- 使用 typer 创建命令行接口
- 使用 pytest 进行测试
- 使用 sqlalchemy 进行数据库交互

## 类型提示

- 所有函数参数和返回值都使用类型提示
- 从 `typing` 模块导入类型
- 使用 `Type | None` 而非 `Optional[Type]`
- 泛型类型使用 `TypeVar`
- 自定义类型定义在 `types.py`
- 使用 `Protocol` 实现鸭子类型

## 文档

- 使用 Google 风格的 docstring
- 文档化所有公开 API
- 保持 README.md 更新
- 使用合适的内联注释
- 生成 API 文档
- 记录环境搭建流程

## 开发流程

- 使用虚拟环境（venv）
- 实现 pre-commit 钩子
- 使用合适的 Git 工作流
- 遵循语义化版本控制
- 实现 CI/CD 流程
- 实现日志记录

## 依赖管理

- 使用 uv 管理依赖
- 固定依赖版本
- 生产环境使用 requirements.txt/pyproject.toml
- 区分开发依赖
- 使用合适的包版本
- 定期更新依赖
- 检查安全漏洞
