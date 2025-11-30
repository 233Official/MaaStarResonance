from typing import cast, Any, List, Tuple

import numpy
from rapidfuzz import fuzz, process

def get_best_match_single(query: str, choices: List[str], score_threshold: float = 60) -> str | None:
    """
    Fuzzy 匹配一个 query 到候选列表，返回分数最高的候选项

    Args:
        query: 输入字符串，只能一个
        choices: 候选字符串列表
        score_threshold: 分数阈值，低于此分数视为不匹配

    Returns:
        最佳匹配字符串，或 None
    """
    if not choices or not query.strip():
        return None

    # 计算 query 与所有候选的相似度 [len(choices)]
    scores = process.cdist(
        queries=[query],
        choices=choices,
        scorer=cast(Any, fuzz.ratio),
        dtype=numpy.float32
    )[0]

    # 找到最高分及其索引
    best_idx = int(numpy.argmax(scores))
    best_score = float(scores[best_idx])

    # 阈值过滤
    if best_score < score_threshold:
        return None

    return choices[best_idx]


def get_best_match_with_score(query: str, choices: List[str], score_threshold: float = 60) -> Tuple[str, float] | None:
    """
    Fuzzy 匹配一个 query 到候选列表，返回分数最高的候选项（带分数）

    Args:
        query: 输入字符串，只能一个
        choices: 候选字符串列表
        score_threshold: 分数阈值，低于此分数视为不匹配

    Returns:
        最佳匹配字符串和分数，或 None
    """
    if not choices or not query.strip():
        return None

    scores = process.cdist(
        queries=[query],
        choices=choices,
        scorer=cast(Any, fuzz.ratio),
        dtype=numpy.float32
    )[0]

    best_idx = int(numpy.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score < score_threshold:
        return None

    return choices[best_idx], best_score


def get_best_match_batch(queries: List[str], choices: List[str], score_threshold: float = 60) -> List[str | None]:
    """
    Fuzzy 匹配多个 query 到候选列表，分别返回分数最高的候选项

    Args:
        queries: 输入字符串列表
        choices: 候选字符串列表
        score_threshold: 分数阈值，低于此分数视为不匹配

    Returns:
        最佳匹配字符串和分数，或 None
    """
    if not choices or not queries:
        return [None] * len(queries)

    scores_matrix = process.cdist(
        queries=queries,
        choices=choices,
        scorer=cast(Any, fuzz.ratio),
        dtype=numpy.float32
    )

    results = []
    for i, scores in enumerate(scores_matrix):
        best_idx = int(numpy.argmax(scores))
        best_score = float(scores[best_idx])
        results.append(choices[best_idx] if best_score >= score_threshold else None)

    return results


def get_best_match_batch_with_score(queries: List[str], choices: List[str], score_threshold: float = 60) -> List[Tuple[str, float] | None]:
    """
    Fuzzy 匹配多个 query 到候选列表，分别返回分数最高的候选项（带分数）

    Args:
        queries: 输入字符串列表
        choices: 候选字符串列表
        score_threshold: 分数阈值，低于此分数视为不匹配

    Returns:
        最佳匹配字符串和分数，或 None
    """
    if not choices or not queries:
        return [None] * len(queries)

    scores_matrix = process.cdist(
        queries=queries,
        choices=choices,
        scorer=cast(Any, fuzz.ratio),
        dtype=numpy.float32
    )

    results = []
    for i, scores in enumerate(scores_matrix):
        best_idx = int(numpy.argmax(scores))
        best_score = float(scores[best_idx])
        results.append((choices[best_idx], best_score) if best_score >= score_threshold else None)

    return results
