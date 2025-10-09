import sys
import subprocess
from pathlib import Path

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
        print(
            "Please run install.py script to install Python runtime environment first."
        )
        sys.exit(1)

    python_executable = embed_python_path / "python.exe"
    if not python_executable.exists():
        print("无法找到 Python 可执行文件，请检查 python 文件夹是否正确")
        print(
            "Cannot find Python executable, please check if the python folder is correct."
        )
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

    print("依赖安装完成，请手动关闭程序然后重新启动程序")


def main():
    if check_req_ready():
        from maa.agent.agent_server import AgentServer
        from maa.toolkit import Toolkit
        import my_action
        import my_reco

        Toolkit.init_option("./")

        socket_id = sys.argv[-1]

        AgentServer.start_up(socket_id)
        AgentServer.join()
        AgentServer.shut_down()
    else:
        print("依赖未安装，开始安装项目依赖...")
        init_python_env()


if __name__ == "__main__":
    main()
