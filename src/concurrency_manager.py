"""
并发控制管理模块
提供线程安全的资源访问控制，防止并发操作导致的资源竞争
"""
import threading
import fcntl
import os
import logging
import uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class FileLock:
    """
    文件锁 - 用于跨进程同步

    适用于需要跨进程保护的资源，如哈希缓存文件。
    """

    def __init__(self, lock_file: str):
        """
        初始化文件锁

        Args:
            lock_file: 锁文件路径
        """
        self.lock_file = Path(lock_file)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._fd: Optional[int] = None

    @contextmanager
    def acquire(self, timeout: float = 10.0):
        """
        获取文件锁

        Args:
            timeout: 获取锁的超时时间(秒)

        Yields:
            None

        Raises:
            TimeoutError: 获取锁超时
        """
        import time

        self._fd = open(self.lock_file, 'w')
        start_time = time.time()

        try:
            # 非阻塞尝试获取锁
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
            return
        except (IOError, BlockingIOError):
            pass

        # 如果获取失败，等待后重试
        while time.time() - start_time < timeout:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX)
                yield
                return
            except (IOError, BlockingIOError):
                time.sleep(0.1)

        raise TimeoutError(f"获取文件锁超时: {self.lock_file}")

    def release(self):
        """释放文件锁"""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
                self._fd.close()
            except Exception:
                pass
            finally:
                self._fd = None


class ThreadSafeCounter:
    """
    线程安全计数器

    用于生成唯一序号。
    """

    def __init__(self, initial: int = 0):
        """
        初始化计数器

        Args:
            initial: 初始值
        """
        self._value = initial
        self._lock = threading.Lock()

    def increment(self) -> int:
        """
        递增并返回新值

        Returns:
            递增后的值
        """
        with self._lock:
            self._value += 1
            return self._value

    def get(self) -> int:
        """
        获取当前值

        Returns:
            当前值
        """
        with self._lock:
            return self._value


class TaskIdGenerator:
    """
    线程安全的任务ID生成器

    生成格式: TASK{timestamp}_{seq}_{uuid}
    例如: TASK20260515120000_0001_a1b2
    """

    _instance = None
    _lock = threading.Lock()
    _counter: Optional[ThreadSafeCounter] = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._counter = ThreadSafeCounter()
        return cls._instance

    def generate(self, prefix: str = "TASK") -> str:
        """
        生成唯一任务ID

        Args:
            prefix: ID前缀

        Returns:
            唯一任务ID
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        seq = self._counter.increment()
        uuid_suffix = uuid.uuid4().hex[:4]
        return f"{prefix}{timestamp}_{seq:04d}_{uuid_suffix}"


class TempDirManager:
    """
    临时目录管理器

    防止并发清理导致的资源冲突。
    """

    _instance = None
    _lock = threading.Lock()
    _active_dirs: set = set()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, dir_path: str):
        """
        注册临时目录

        Args:
            dir_path: 目录路径
        """
        with self._lock:
            self._active_dirs.add(dir_path)

    def unregister(self, dir_path: str):
        """
        取消注册临时目录

        Args:
            dir_path: 目录路径
        """
        with self._lock:
            self._active_dirs.discard(dir_path)

    def cleanup(self, dir_path: str):
        """
        安全清理临时目录

        Args:
            dir_path: 目录路径
        """
        import shutil

        with self._lock:
            if dir_path in self._active_dirs:
                self._active_dirs.discard(dir_path)
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
                    logger.info(f"已清理临时目录: {dir_path}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")

    def is_active(self, dir_path: str) -> bool:
        """
        检查目录是否活跃

        Args:
            dir_path: 目录路径

        Returns:
            是否活跃
        """
        with self._lock:
            return dir_path in self._active_dirs


# 全局实例
task_id_generator = TaskIdGenerator()
temp_dir_manager = TempDirManager()
