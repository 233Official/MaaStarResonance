from datetime import datetime, timedelta


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


def format_seconds_to_ms(seconds: float) -> str:
    """
    将秒数转换为 'xx分钟xx秒' 格式

    Args:
        seconds: 时间差（秒）

    Returns:
        字符串，如 '2分钟30秒'
    """
    seconds = int(seconds)
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}分钟{sec}秒"


def get_current_timestamp() -> int:
    """
    获取当前时间戳（单位：秒）

    Returns:
        int类型时间戳，如 1698115200
    """
    return int(datetime.now().timestamp())


def get_current_timestamp_ms() -> int:
    """
    获取当前时间戳（单位：毫秒）

    Returns:
        int类型时间戳，毫秒级
    """
    return int(datetime.now().timestamp() * 1000)


def str_to_datetime(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    将时间字符串转换为 datetime 对象

    Args:
        time_str: 时间字符串，例如 '2025-11-24 13:45:00'
        fmt: 格式字符串，默认 '%Y-%m-%d %H:%M:%S'

    Returns:
        datetime对象
    """
    return datetime.strptime(time_str, fmt)


def datetime_to_str(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    将 datetime 对象格式化为时间字符串

    Args:
        dt: datetime对象
        fmt: 格式字符串，默认 '%Y-%m-%d %H:%M:%S'

    Returns:
        格式化后的时间字符串
    """
    return dt.strftime(fmt)


def timestamp_to_str(ts: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    时间戳转为指定格式的字符串

    Args:
        ts: 时间戳（单位：秒）
        fmt: 格式字符串，默认 '%Y-%m-%d %H:%M:%S'

    Returns:
        格式化后的时间字符串
    """
    return datetime.fromtimestamp(ts).strftime(fmt)


def str_to_timestamp(time_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> int:
    """
    字符串时间转为秒级时间戳

    Args:
        time_str: 时间字符串
        fmt: 时间格式字符串

    Returns:
        int类型时间戳
    """
    dt = datetime.strptime(time_str, fmt)
    return int(dt.timestamp())


def add_days(date_obj: datetime, days: int) -> datetime:
    """
    给指定日期增加或减少天数

    Args:
        date_obj: datetime类型日期
        days: 增加的天数，可为负数

    Returns:
        增加后的日期对象
    """
    return date_obj + timedelta(days=days)


def diff_days(date1: datetime, date2: datetime) -> int:
    """
    计算两个日期的相差天数

    Args:
        date1: 第一个日期
        date2: 第二个日期

    Returns:
        天数差，int类型
    """
    delta = date1 - date2
    return abs(delta.days)


def diff_seconds(date1: datetime, date2: datetime) -> int:
    """
    计算两个日期的相差秒数

    Args:
        date1: 第一个日期
        date2: 第二个日期

    Returns:
        秒数差，int类型
    """
    delta = date1 - date2
    return abs(int(delta.total_seconds()))