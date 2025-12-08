# 这里存放一些工具类
# 封装一些 print 方法
def print_info(message: str) -> None:
    print(f"info: {message}")


def print_error(message: str) -> None:
    print(f"error: {message}")


def print_debug(message: str) -> None:
    print(f"debug: {message}")


def print_warning(message: str) -> None:
    print(f"warning: {message}")
