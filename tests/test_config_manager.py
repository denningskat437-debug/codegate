"""
配置管理模块单元测试
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml


class TestConfigManagerInit:
    """初始化测试"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        from src.config_manager import ConfigManager
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2

    def test_singleton_reset(self):
        """测试单例重置"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()
        assert config is not None
        ConfigManager._instance = None  # 清理


class TestConfigManagerGet:
    """get 方法测试"""

    def test_get_existing_key(self):
        """测试获取存在的键"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('server.host')
        assert result is not None

    def test_get_nonexistent_key_with_default(self):
        """测试获取不存在的键返回默认值"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('nonexistent.key', 'default_value')
        assert result == 'default_value'

    def test_get_nested_key(self):
        """测试获取嵌套键"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('server.port')
        assert result == 8000

    def test_get_top_level_key(self):
        """测试获取顶级键"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('server')
        assert isinstance(result, dict)


class TestConfigManagerGetAll:
    """配置字典访问测试"""

    def test_get_server_config(self):
        """测试获取服务器配置"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('server')
        assert isinstance(result, dict)
        assert 'host' in result
        assert 'port' in result

    def test_get_logging_config(self):
        """测试获取日志配置"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        result = config.get('logging')
        assert isinstance(result, dict)
        assert 'level' in result


class TestConfigManagerReload:
    """reload 方法测试"""

    def test_reload_resets_config(self):
        """测试重载重置配置"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        original = config.get('server.port')
        config.reload()
        reloaded = config.get('server.port')

        assert original == reloaded


class TestConfigManagerEnvironmentOverride:
    """环境变量覆盖测试"""

    def test_env_override_disabled(self):
        """测试环境变量覆盖关闭"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None

        original_env = os.environ.get('CODEGATE_SERVER_PORT')
        try:
            os.environ['CODEGATE_SERVER_PORT'] = '9999'
            # 默认不启用环境变量覆盖
            config = ConfigManager()
            result = config.get('server.port')
            # 应该还是配置文件的值
            assert result == 8000
        finally:
            if original_env:
                os.environ['CODEGATE_SERVER_PORT'] = original_env
            else:
                os.environ.pop('CODEGATE_SERVER_PORT', None)


class TestConfigManagerPaths:
    """路径配置测试"""

    def test_paths_exist(self):
        """测试路径配置存在"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        assert config.get('paths.cache_dir') is not None
        assert config.get('paths.report_dir') is not None
        assert config.get('paths.log_dir') is not None


class TestConfigManagerEmail:
    """邮件配置测试"""

    def test_email_config_exists(self):
        """测试邮件配置存在"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        email_config = config.get('email')
        assert email_config is not None
        # email.enabled 现在默认为 true
        assert config.get('email.smtp_host') is not None

    def test_email_base_url_exists(self):
        """测试邮件 base_url 配置存在"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        base_url = config.get('email.base_url')
        assert base_url is not None


class TestConfigManagerUserMapping:
    """用户映射配置测试"""

    def test_user_mapping_config_exists(self):
        """测试用户映射配置存在"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        assert config.get('user_mapping.enabled') is True
        assert config.get('user_mapping.file') == 'data/user_mapping.xlsx'


class TestConfigManagerRisk:
    """风险配置测试"""

    def test_risk_config_exists(self):
        """测试风险配置存在"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        risk = config.get('risk')
        assert risk is not None
        assert 'thresholds' in risk

    def test_risk_thresholds(self):
        """测试风险阈值配置"""
        from src.config_manager import ConfigManager
        ConfigManager._instance = None
        config = ConfigManager()

        high = config.get('risk.thresholds.high')
        assert high['min'] == 70
        assert high['action'] == 'reject'
