import numpy
from rapidfuzz import fuzz, process

from logger import logger


def print_center_block(lines: list[str], total_width: int = 40, border_char: str = "#"):
    """
    让多行文本在固定宽度内居中显示，并加边框。
    :param lines: 要显示的文本（列表，每行一个字符串）
    :param total_width: 总宽度
    :param border_char: 边框字符
    """
    # 打印顶部边框
    logger.info(border_char * int(total_width * 1.3))
    for line in lines:
        logger.info(line.center(total_width))
    # 打印底部边框
    logger.info(border_char * int(total_width * 1.3))


def get_best_match_single(query: str, choices: list[str], score_threshold: float = 60) -> str | None:
    """
    Fuzzy 匹配一个 query 到候选列表，返回分数最高的候选项

    Args:
        query: 输入字符串，只能一个
        choices: 候选字符串列表
        score_threshold: 分数阈值，低于此分数视为不匹配
        min_score_diff: 分数差阈值，避免接近分数的误判
    
    Returns:
        最佳匹配字符串，或 None
    """
    if not choices or not query.strip():
        return None

    # 计算 query 与所有候选的相似度 [len(choices)]
    scores = process.cdist(
        [query], 
        choices,
        scorer=fuzz.ratio,
        dtype=numpy.float32
    )[0]

    # 找到最高分及其索引
    best_idx = int(numpy.argmax(scores))
    best_score = float(scores[best_idx])

    # 阈值过滤
    if best_score < score_threshold:
        return None

    return choices[best_idx]


def format_seconds_to_hms(seconds: float) -> str:
    """
    将秒数转换为 'xx小时xx分钟xx秒' 格式

    Args:
        seconds: 时间差（秒）
    
    Returns:
        字符串，如 '1小时2分钟3秒'
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hours}小时{minutes}分钟{sec}秒"
