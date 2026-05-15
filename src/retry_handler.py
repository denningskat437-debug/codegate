"""
重试处理模块
提供统一的重试装饰器和配置，用于处理外部服务调用的临时故障
"""
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from typing import Callable

logger = logging.getLogger(__name__)

# 网络相关异常类型
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    ConnectionRefusedError,
    ConnectionResetError,
    OSError,
)


def retry_claude_sdk(
    max_attempts: int = 3,
    wait_min: float = 2.0,
    wait_max: float = 30.0
) -> Callable:
    """
    Claude SDK 调用重试装饰器

    使用指数退避策略，适用于 API 限流和网络抖动场景。

    Args:
        max_attempts: 最大重试次数，默认 3 次
        wait_min: 最小等待时间(秒)，默认 2 秒
        wait_max: 最大等待时间(秒)，默认 30 秒

    Returns:
        装饰器函数

    Example:
        @retry_claude_sdk(max_attempts=3, wait_min=2.0, wait_max=30.0)
        async def _analyze_async(self):
            # Claude SDK 调用
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG),
        reraise=True
    )


def retry_git_operation(
    max_attempts: int = 3,
    wait_seconds: float = 5.0
) -> Callable:
    """
    Git 操作重试装饰器

    使用固定等待时间，适用于 Git 克隆、拉取等操作。

    Args:
        max_attempts: 最大重试次数，默认 3 次
        wait_seconds: 固定等待时间(秒)，默认 5 秒

    Returns:
        装饰器函数

    Example:
        @retry_git_operation(max_attempts=3, wait_seconds=5.0)
        def clone(self):
            # Git 克隆操作
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(wait_seconds),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"Git 操作失败，{wait_seconds}秒后重试 (第{retry_state.attempt_number}次)"
        ),
        reraise=True
    )


def retry_network_operation(
    max_attempts: int = 3,
    max_delay: float = 30.0,
    wait_min: float = 1.0,
    wait_max: float = 10.0
) -> Callable:
    """
    网络操作重试装饰器

    仅对网络相关异常进行重试，适用于 HTTP 请求等场景。

    Args:
        max_attempts: 最大重试次数，默认 3 次
        max_delay: 最大总延迟时间(秒)，默认 30 秒
        wait_min: 最小等待时间(秒)，默认 1 秒
        wait_max: 最大等待时间(秒)，默认 10 秒

    Returns:
        装饰器函数
    """
    return retry(
        stop=(stop_after_attempt(max_attempts) | stop_after_delay(max_delay)),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(NETWORK_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
