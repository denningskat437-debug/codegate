"""
HashChecker 单元测试
测试哈希检测模块的所有公共方法
"""
import pytest
import os
from pathlib import Path
from src.hash_checker import HashChecker


class TestHashCheckerInit:
    """测试初始化"""

    def test_init_default_cache_dir(self, temp_dir):
        """测试默认缓存目录"""
        checker = HashChecker(cache_dir=temp_dir)
        assert Path(temp_dir).exists()

    def test_init_custom_cache_dir(self, temp_dir):
        """测试自定义缓存目录"""
        custom_dir = os.path.join(temp_dir, 'custom_cache')
        checker = HashChecker(cache_dir=custom_dir)
        assert Path(custom_dir).exists()


class TestHashCheckerCache:
    """测试缓存读写"""

    def test_get_cached_hash_not_exists(self, temp_dir):
        """测试获取不存在的缓存"""
        checker = HashChecker(cache_dir=temp_dir)
        result = checker.get_cached_hash('nonexistent_project')
        assert result is None

    def test_save_and_get_hash(self, temp_dir):
        """测试保存和获取哈希"""
        checker = HashChecker(cache_dir=temp_dir)

        # 保存哈希
        checker.save_hash('test_project', 'abc123hash')

        # 获取哈希
        cached = checker.get_cached_hash('test_project')
        assert cached == 'abc123hash'

    def test_save_multiple_hashes(self, temp_dir):
        """测试保存多个项目的哈希"""
        checker = HashChecker(cache_dir=temp_dir)

        checker.save_hash('project_a', 'hash_a')
        checker.save_hash('project_b', 'hash_b')
        checker.save_hash('project_c', 'hash_c')

        assert checker.get_cached_hash('project_a') == 'hash_a'
        assert checker.get_cached_hash('project_b') == 'hash_b'
        assert checker.get_cached_hash('project_c') == 'hash_c'

    def test_overwrite_hash(self, temp_dir):
        """测试覆盖已有哈希"""
        checker = HashChecker(cache_dir=temp_dir)

        checker.save_hash('test_project', 'old_hash')
        checker.save_hash('test_project', 'new_hash')

        assert checker.get_cached_hash('test_project') == 'new_hash'

    def test_clear_cache(self, temp_dir):
        """测试清除缓存"""
        checker = HashChecker(cache_dir=temp_dir)

        checker.save_hash('test_project', 'abc123')
        checker.clear_cache('test_project')

        assert checker.get_cached_hash('test_project') is None

    def test_clear_nonexistent_cache(self, temp_dir):
        """测试清除不存在的缓存（不应报错）"""
        checker = HashChecker(cache_dir=temp_dir)
        # 不应抛出异常
        checker.clear_cache('nonexistent_project')


class TestHashCheckerFileHash:
    """测试文件哈希计算"""

    def test_calculate_file_hash_empty_dir(self, temp_dir):
        """测试空目录的哈希"""
        checker = HashChecker(cache_dir=temp_dir)
        hash_value = checker._calculate_file_hash(temp_dir)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 输出 64 字符

    def test_calculate_file_hash_consistency(self, sample_code_dir):
        """测试相同内容产生相同哈希"""
        checker = HashChecker()
        hash1 = checker._calculate_file_hash(sample_code_dir)
        hash2 = checker._calculate_file_hash(sample_code_dir)
        assert hash1 == hash2

    def test_calculate_file_hash_changes_with_content(self, temp_dir):
        """测试内容变化导致哈希变化"""
        code_dir = Path(temp_dir) / 'code'
        code_dir.mkdir()

        # 创建文件
        (code_dir / 'test.py').write_text('print("hello")')

        checker = HashChecker()
        hash1 = checker._calculate_file_hash(str(code_dir))

        # 修改文件
        (code_dir / 'test.py').write_text('print("world")')

        hash2 = checker._calculate_file_hash(str(code_dir))
        assert hash1 != hash2

    def test_calculate_file_hash_ignores_hidden_files(self, temp_dir):
        """测试忽略隐藏文件"""
        code_dir = Path(temp_dir) / 'code'
        code_dir.mkdir()

        (code_dir / 'visible.py').write_text('print("hello")')
        (code_dir / '.hidden').write_text('secret')

        checker = HashChecker()
        hash1 = checker._calculate_file_hash(str(code_dir))

        # 修改隐藏文件不应影响哈希
        (code_dir / '.hidden').write_text('changed')
        hash2 = checker._calculate_file_hash(str(code_dir))

        assert hash1 == hash2

    def test_calculate_file_hash_multiple_files(self, sample_code_dir):
        """测试多文件目录的哈希"""
        checker = HashChecker()
        hash_value = checker._calculate_file_hash(sample_code_dir)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64


class TestHashCheckerGetHash:
    """测试 get_hash 方法"""

    def test_get_hash_with_git(self, temp_dir):
        """测试获取 git 仓库的哈希"""
        import subprocess

        # 创建一个 git 仓库
        repo_dir = Path(temp_dir) / 'git_repo'
        repo_dir.mkdir()

        subprocess.run(['git', 'init'], cwd=repo_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'test'], cwd=repo_dir, capture_output=True)

        (repo_dir / 'test.py').write_text('print("hello")')
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo_dir, capture_output=True)

        checker = HashChecker()
        hash_value = checker.get_hash(str(repo_dir))
        assert isinstance(hash_value, str)
        assert len(hash_value) == 40  # Git commit hash 是 40 字符

    def test_get_hash_without_git(self, sample_code_dir):
        """测试非 git 目录使用文件哈希"""
        checker = HashChecker()
        hash_value = checker.get_hash(sample_code_dir)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # 文件哈希是 64 字符
