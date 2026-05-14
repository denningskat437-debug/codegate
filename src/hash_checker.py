"""
代码哈希检测模块
用于检测代码是否发生变化，避免重复检测
"""
import hashlib
import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class HashChecker:
    """代码哈希检测器"""

    def __init__(self, cache_dir: str = 'cache/hashes'):
        """
        初始化哈希检测器

        Args:
            cache_dir: 哈希缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_hash(self, code_path: str) -> str:
        """
        计算代码目录的哈希值
        优先使用 git commit hash，失败则计算文件哈希

        Args:
            code_path: 代码目录路径

        Returns:
            哈希值字符串
        """
        # 优先使用 git commit hash
        try:
            result = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=code_path,
                stderr=subprocess.DEVNULL
            )
            commit_hash = result.decode().strip()
            logger.info(f"获取到 git commit hash: {commit_hash[:8]}...")
            return commit_hash
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("无法获取 git hash，使用文件哈希")
            return self._calculate_file_hash(code_path)

    def _calculate_file_hash(self, code_path: str) -> str:
        """
        计算所有文件的哈希

        Args:
            code_path: 代码目录路径

        Returns:
            文件内容的 SHA256 哈希值
        """
        hasher = hashlib.sha256()

        for root, dirs, files in os.walk(code_path):
            # 排除 .git 目录和其他隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in sorted(files):
                # 排除隐藏文件
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        # 使用文件路径和内容计算哈希
                        hasher.update(file_path.encode('utf-8'))
                        hasher.update(f.read())
                except (IOError, PermissionError) as e:
                    logger.warning(f"无法读取文件 {file_path}: {e}")
                    continue

        return hasher.hexdigest()

    def get_cached_hash(self, project_name: str) -> str:
        """
        获取缓存的哈希值

        Args:
            project_name: 项目名称

        Returns:
            缓存的哈希值，不存在则返回 None
        """
        cache_file = self.cache_dir / f"{project_name}.hash"
        if cache_file.exists():
            cached = cache_file.read_text().strip()
            logger.info(f"获取到缓存哈希: {cached[:8]}...")
            return cached
        return None

    def save_hash(self, project_name: str, hash_value: str):
        """
        保存哈希值到缓存

        Args:
            project_name: 项目名称
            hash_value: 哈希值
        """
        cache_file = self.cache_dir / f"{project_name}.hash"
        cache_file.write_text(hash_value)
        logger.info(f"已保存哈希缓存: {hash_value[:8]}...")

    def clear_cache(self, project_name: str):
        """
        清除指定项目的哈希缓存

        Args:
            project_name: 项目名称
        """
        cache_file = self.cache_dir / f"{project_name}.hash"
        if cache_file.exists():
            cache_file.unlink()
            logger.info(f"已清除哈希缓存: {project_name}")
