# 初始化开发环境
from pathlib import Path
import platform
from agent.logger import logger
import shutil

CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = (Path(__file__).parent / "..").resolve()


# 识别当前系统环境
def identify_system_environment() -> str:
    system = platform.system()
    if system == "Windows":
        platform_info = "windows"
    elif system == "Darwin":
        platform_info = "macos"
    elif system == "Linux":
        platform_info = "linux"
    else:
        platform_info = "unknown"
    logger.info(f"当前系统环境为: {platform_info}")
    return platform_info


# 检查 Submodule 目录是否存在
def check_submodule_directories():
    maa_common_assets_dir = PROJECT_ROOT / "assets" / "MaaCommonAssets"
    required_dirs = [
        maa_common_assets_dir,
    ]
    missing_dirs = [str(dir) for dir in required_dirs if not dir.exists()]
    if missing_dirs:
        logger.error("以下子模块目录缺失，请先初始化并更新子模块:")
        for dir in missing_dirs:
            logger.error(f"- {dir}")
        logger.error("请运行以下命令以初始化和更新子模块:")
        logger.error("git submodule update --init --recursive")
        exit(1)
    else:
        logger.info("所有子模块目录均已存在。")


# 判断 deps 目录下是否存在 bin 目录
def check_deps_bin_directory():
    deps_dir = PROJECT_ROOT / "deps"
    bin_dir = deps_dir / "bin"
    if not bin_dir.exists():
        logger.error(f"检测到 MaaFramework Release 依赖缺失")
        logger.error(
            "请下载 MaaFramework 的 Release 包: https://github.com/MaaXYZ/MaaFramework/releases, 解压到 deps 文件夹中"
        )
        exit(1)
    else:
        logger.info("必要的依赖目录已存在。")


# 判断虚拟环境是否存在
def check_virtual_environment():
    venv_dir = PROJECT_ROOT / ".venv"
    if not venv_dir.exists():
        logger.error(f"检测到虚拟环境缺失")
        logger.error("请先运行 uv sync 命令以创建虚拟环境")
        logger.error(
            "如果你是用其他方式创建虚拟环境, 且不在 .venv 目录下, 请忽略此提示并确保 assets/interface.json 中的 child_exec 路径正确"
        )
    else:
        logger.info("虚拟环境已存在。")


# 配置 ocr 模型目录
def check_ocr_model_directory():
    maa_common_assets_dir = PROJECT_ROOT / "assets" / "MaaCommonAssets"
    default_ocr_model_source = maa_common_assets_dir / "OCR" / "ppocr_v5" / "zh_cn"

    ocr_model_dir = PROJECT_ROOT / "assets" / "resource" / "base" / "model" / "ocr"
    if not ocr_model_dir.exists():
        shutil.copytree(
            default_ocr_model_source,
            ocr_model_dir,
            dirs_exist_ok=True,
        )
        logger.info("默认 OCR 模型已复制到资源目录。")
    else:
        logger.info("OCR 模型目录已存在。")


if __name__ == "__main__":
    platform_info = identify_system_environment()
    check_submodule_directories()
    check_deps_bin_directory()
    check_virtual_environment()
    check_ocr_model_directory()
    logger.info("开发环境初始化完成。")
