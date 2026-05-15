"""
Git 操作处理器
负责克隆仓库、获取代码差异、清理临时目录
"""
import subprocess
import os
import tempfile
import shutil
import logging

# 导入重试装饰器和并发控制
from src.retry_handler import retry_git_operation
from src.concurrency_manager import temp_dir_manager

logger = logging.getLogger(__name__)


class GitHandler:
    """Git 操作处理器"""

    def __init__(self, repo_url: str, branch: str = 'main'):
        """
        初始化 Git 处理器

        Args:
            repo_url: 仓库地址
            branch: 分支名称，默认 main
        """
        self.repo_url = repo_url
        self.branch = branch
        self.repo_dir = None

    @retry_git_operation(max_attempts=3, wait_seconds=5.0)
    def clone(self) -> str:
        """
        克隆仓库到临时目录

        Returns:
            代码目录路径
        """
        self.repo_dir = tempfile.mkdtemp(prefix='codegate_')
        # 注册临时目录到管理器
        temp_dir_manager.register(self.repo_dir)
        logger.info(f"开始克隆仓库: {self.repo_url} -> {self.repo_dir}")

        try:
            subprocess.run(
                ['git', 'clone', '-b', self.branch, '--depth', '2', self.repo_url, self.repo_dir],
                capture_output=True,
                check=True,
                timeout=300  # 5分钟超时
            )
            logger.info(f"仓库克隆成功: {self.repo_dir}")
            return self.repo_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"克隆失败: {e.stderr.decode() if e.stderr else str(e)}")
            self.cleanup()
            raise RuntimeError(f"克隆仓库失败: {self.repo_url}")
        except subprocess.TimeoutExpired:
            logger.error("克隆超时")
            self.cleanup()
            raise RuntimeError("克隆仓库超时")

    def get_diff(self, base: str = 'HEAD~1') -> str:
        """
        获取代码变更差异

        Args:
            base: 对比的基准，默认 HEAD~1

        Returns:
            diff 文本
        """
        if not self.repo_dir:
            raise RuntimeError("请先调用 clone() 方法")

        try:
            result = subprocess.check_output(
                ['git', 'diff', base, 'HEAD'],
                cwd=self.repo_dir,
                stderr=subprocess.STDOUT
            )
            return result.decode('utf-8', errors='replace')
        except subprocess.CalledProcessError:
            # 如果是首次提交，尝试获取所有文件
            try:
                result = subprocess.check_output(
                    ['git', 'show', '--stat'],
                    cwd=self.repo_dir
                )
                return result.decode('utf-8', errors='replace')
            except:
                return ""

    def get_commit_info(self) -> dict:
        """
        获取最新提交信息

        Returns:
            包含 commit_id, author, message 的字典
        """
        if not self.repo_dir:
            raise RuntimeError("请先调用 clone() 方法")

        try:
            commit_id = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_dir
            ).decode().strip()

            author = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=format:%an'],
                cwd=self.repo_dir
            ).decode().strip()

            message = subprocess.check_output(
                ['git', 'log', '-1', '--pretty=format:%s'],
                cwd=self.repo_dir
            ).decode().strip()

            return {
                'commit_id': commit_id,
                'author': author,
                'message': message
            }
        except subprocess.CalledProcessError:
            return {
                'commit_id': '',
                'author': '',
                'message': ''
            }

    def cleanup(self):
        """清理临时目录 (使用并发安全管理器)"""
        if self.repo_dir:
            temp_dir_manager.cleanup(self.repo_dir)
            self.repo_dir = None
