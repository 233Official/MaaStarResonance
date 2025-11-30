from agent.logger import logger


def print_center_block(lines: list[str], total_width: int = 40, border_char: str = "#"):
    """
    让多行文本在固定宽度内居中显示，并加边框。

    Args:
        lines: 要显示的文本（列表，每行一个字符串）
        total_width: 总宽度
        border_char: 边框字符

    Returns:
        打印的字符串
    """
    # 打印顶部边框
    logger.info(border_char * int(total_width * 1.3))
    for line in lines:
        logger.info(line.center(total_width))
    # 打印底部边框
    logger.info(border_char * int(total_width * 1.3))
