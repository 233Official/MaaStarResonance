import subprocess
import sys
from pathlib import Path

# 补充当前路径和上级路径
CURRENT_DIR = Path(__file__).parent.resolve()
PARENT_DIR = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

PROJECT_ROOT = (Path(__file__).parent / "..").resolve()
WHEELS_DIR = PROJECT_ROOT / "deps" / "wheels"


def check_req_ready() -> bool:
    """通过尝试 import maa 来检查依赖是否安装完成"""
    try:
        import maa  # noqa: F401

        print("maa imported successfully")
        return True
    except ImportError:
        print("maa import failed")
        return False


def init_python_env():
    """离线安装 pip, setuptools, wheel 以及项目依赖"""
    embed_python_path = PROJECT_ROOT / "python"
    if not embed_python_path.exists():
        print("请先运行 install.py 脚本安装 Python 运行环境")
        print("Please run install.py script to install Python runtime environment first.")
        sys.exit(1)

    python_executable = embed_python_path / "python.exe"
    if not python_executable.exists():
        print("无法找到 Python 可执行文件，请检查 python 文件夹是否正确")
        print("Cannot find Python executable, please check if the python folder is correct.")
        sys.exit(1)

    # 安装 pip
    get_pip_script = PROJECT_ROOT / "deps" / "get-pip.py"
    if not get_pip_script.exists():
        print("无法找到 get-pip.py，请检查 deps 文件夹是否正确")
        print("Cannot find get-pip.py, please check if the deps folder is correct.")
        sys.exit(1)

    subprocess.check_call(
        [
            str(python_executable),
            str(get_pip_script),
            "--no-index",
            f"--find-links={WHEELS_DIR}",
        ]
    )

    # 安装 setuptools 和 wheel
    subprocess.check_call(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "setuptools",
            "wheel",
        ]
    )

    # 安装项目依赖
    subprocess.check_call(
        [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "--no-index",
            f"--find-links={WHEELS_DIR}",
            "--no-build-isolation",
            f"{PROJECT_ROOT}",
        ]
    )

    # 安装完成后让当前进程也能看到刚写进的 site-packages
    site_packages = (PROJECT_ROOT / "python" / "Lib" / "site-packages").resolve()
    if site_packages.exists() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))
    import importlib
    importlib.invalidate_caches()

    print("Python 依赖安装/更新 已完成\n")


def main():
    print(f"开始安装/更新 Python 依赖")

    # 开发时应当注释下面两行, 编译时自动解除注释
    # init_python_env()

    # 导入MAA工具
    from maa.agent.agent_server import AgentServer
    from maa.toolkit import Toolkit

    # 导入整个 Agent 包
    import agent
    _ = agent

    # 导入基础包
    from agent.logger import logger
    from agent.module_loader import load_plugins

    logger.info("===== 开始初始化MAA模块包 =====")

    # 加载 Agent 包下所有的文件夹
    for item in CURRENT_DIR.iterdir():
        # 跳过 __pycache__
        if item.is_dir() and item.name != "__pycache__":
            load_plugins(str(item), f"agent.{item.name}")
            logger.info(f"> 子模块 {item.name} 加载完成！")

    logger.info("===== MAA模块包初始化完成 =====\n")

    Toolkit.init_option("./")

    socket_id = sys.argv[-1]
    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
