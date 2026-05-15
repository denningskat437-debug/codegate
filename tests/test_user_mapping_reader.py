"""
用户映射读取模块单元测试
"""
import pytest
import pandas as pd
from pathlib import Path
from src.user_mapping_reader import UserMappingReader


class TestUserMappingReaderInit:
    """初始化测试"""

    def test_init_with_valid_path(self, tmp_path):
        """测试有效路径初始化"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'用户名': ['test'], '邮箱': ['test@test.com']})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        assert reader.file_path == file_path

    def test_init_with_nonexistent_path(self):
        """测试不存在的路径初始化（不立即报错）"""
        reader = UserMappingReader("nonexistent.xlsx")
        assert reader.file_path == Path("nonexistent.xlsx")


class TestUserMappingReaderRead:
    """读取功能测试"""

    def test_read_valid_file(self, tmp_path):
        """测试读取有效文件"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({
            '用户名': ['user1', 'user2'],
            '邮箱': ['user1@test.com', 'user2@test.com']
        })
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        mapping = reader.read()

        assert len(mapping) == 2
        assert mapping['user1'] == 'user1@test.com'
        assert mapping['user2'] == 'user2@test.com'

    def test_read_file_not_found(self):
        """测试文件不存在"""
        reader = UserMappingReader("nonexistent.xlsx")
        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_invalid_extension(self, tmp_path):
        """测试无效扩展名"""
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")

        reader = UserMappingReader(str(file_path))
        with pytest.raises(ValueError, match="不支持的文件格式"):
            reader.read()

    def test_read_missing_required_column(self, tmp_path):
        """测试缺少必需列"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'邮箱': ['test@test.com']})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        with pytest.raises(ValueError, match="缺少必需列"):
            reader.read()

    def test_read_empty_file(self, tmp_path):
        """测试空文件"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'用户名': [], '邮箱': []})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        mapping = reader.read()
        assert len(mapping) == 0

    def test_read_handles_nan_values(self, tmp_path):
        """测试处理 NaN 值"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({
            '用户名': ['user1', pd.NA, 'user3'],
            '邮箱': ['user1@test.com', 'user2@test.com', pd.NA]
        })
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        mapping = reader.read()

        # 只有 user1 有有效的用户名和邮箱
        assert 'user1' in mapping
        assert mapping['user1'] == 'user1@test.com'

    def test_read_strips_whitespace(self, tmp_path):
        """测试去除空白字符"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({
            '用户名': ['  user1  ', 'user2'],
            '邮箱': ['  user1@test.com  ', 'user2@test.com']
        })
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        mapping = reader.read()

        assert mapping['user1'] == 'user1@test.com'


class TestUserMappingReaderGetEmail:
    """get_email 方法测试"""

    def test_get_email_existing_user(self, tmp_path):
        """测试获取存在用户的邮箱"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({
            '用户名': ['user1', 'user2'],
            '邮箱': ['user1@test.com', 'user2@test.com']
        })
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        email = reader.get_email('user1')

        assert email == 'user1@test.com'

    def test_get_email_nonexistent_user(self, tmp_path):
        """测试获取不存在用户的邮箱"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'用户名': ['user1'], '邮箱': ['user1@test.com']})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        email = reader.get_email('nonexistent')

        assert email is None

    def test_get_email_uses_cache(self, tmp_path):
        """测试使用缓存"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'用户名': ['user1'], '邮箱': ['user1@test.com']})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))

        # 第一次调用
        email1 = reader.get_email('user1')
        # 第二次调用应该使用缓存
        email2 = reader.get_email('user1')

        assert email1 == email2 == 'user1@test.com'


class TestUserMappingReaderReload:
    """reload 方法测试"""

    def test_reload_clears_cache(self, tmp_path):
        """测试重载清除缓存"""
        file_path = tmp_path / "test_mapping.xlsx"
        df = pd.DataFrame({'用户名': ['user1'], '邮箱': ['user1@test.com']})
        df.to_excel(file_path, index=False)

        reader = UserMappingReader(str(file_path))
        reader.get_email('user1')  # 加载缓存

        reader.reload()

        assert reader._mapping_cache is None
