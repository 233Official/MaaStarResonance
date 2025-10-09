from pathlib import Path

import shutil
import sys
import json

from configure import configure_ocr_model


working_dir = (Path(__file__).parent / "..").resolve()
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print("Please download the MaaFramework to \"deps\" first.")
        print("请先下载 MaaFramework 到 \"deps\"。")
        sys.exit(1)

    shutil.copytree(
        working_dir / "deps" / "bin",
        install_path,
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
        ),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "MaaAgentBinary",
        dirs_exist_ok=True,
    )


def install_resource():

    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )
    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = json.load(f)

    interface["version"] = version

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )

def install_agent():
    shutil.copytree(
        working_dir / "agent",
        install_path / "agent",
        dirs_exist_ok=True,
    )
    # # 为 agent/main.py 取消 line69 的注释
    # main_py_path = install_path / "agent" / "main.py"
    # with open(main_py_path, "r", encoding="utf-8") as f:
    #     lines = f.readlines()
    # with open(main_py_path, "w", encoding="utf-8") as f:
    #     for line in lines:
    #         if line.strip() == "# init_python_env()":
    #             f.write("init_python_env()\n")
    #         else:
    #             f.write(line)

# 安装 embeddable python
def install_embed_python():
    embed_python_zip_path = working_dir / "resource" / "python-3.13.7-embed-amd64.zip"
    embed_python_install_path = install_path / "python"
    # 解压 zip 文件到目标路径
    shutil.unpack_archive(embed_python_zip_path, embed_python_install_path, 'zip')
    # 修改 install_path / "python/python313._pth" 文件, 添加一行 "import site" 以及"..\agent"
    pth_file_path = embed_python_install_path / "python313._pth"
    with open(pth_file_path, "a", encoding="utf-8") as f:
        f.write("\nimport site\n")
        f.write(r"..\agent")

# 拷贝 python wheels 以及 get-pip.py 和 pyproject.toml
def copy_python_wheels():
    wheels_source_path = working_dir / "resource" / "wheels"
    wheels_target_path = install_path / "deps" / "wheels"
    shutil.copytree(wheels_source_path, wheels_target_path, dirs_exist_ok=True)

    get_pip_source_path = working_dir / "resource" / "get-pip.py"
    get_pip_target_path = install_path / "deps" / "get-pip.py"
    shutil.copy2(get_pip_source_path, get_pip_target_path)

    pyproject_source_path = working_dir / "pyproject.toml"
    pyproject_target_path = install_path / "pyproject.toml"
    shutil.copy2(pyproject_source_path, pyproject_target_path)

if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_embed_python()
    copy_python_wheels()

    print(f"Install to {install_path} successfully.")