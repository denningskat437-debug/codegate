"""
配置管理模块
支持多环境配置和配置热加载
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    配置管理器

    支持功能：
    - 主配置文件加载
    - 环境特定配置覆盖
    - 点分隔路径获取配置值
    - 风险规则配置集成
    """

    _instance = None
    _config = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化配置管理器"""
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """加载配置文件"""
        # 确定配置目录
        config_dir = Path(__file__).parent.parent / 'configs'

        # 加载主配置
        main_config_path = config_dir / 'config.yml'
        if main_config_path.exists():
            try:
                with open(main_config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"已加载主配置: {main_config_path}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
                self._config = self._default_config()
        else:
            self._config = self._default_config()
            logger.warning(f"配置文件不存在: {main_config_path}，使用默认配置")

        # 加载环境特定配置
        env = os.getenv('CODEGATE_ENV', 'production')
        if env != 'production':
            env_config_path = config_dir / f'config.{env}.yml'
            if env_config_path.exists():
                try:
                    with open(env_config_path, 'r', encoding='utf-8') as f:
                        env_config = yaml.safe_load(f) or {}
                        self._merge_config(env_config)
                        logger.info(f"已加载环境配置: {env}")
                except Exception as e:
                    logger.warning(f"加载环境配置失败: {e}")

        # 加载风险规则配置
        risk_rules_file = self.get('risk.rules_file', 'configs/risk_rules.yml')
        risk_rules_path = Path(__file__).parent.parent / risk_rules_file
        if risk_rules_path.exists():
            try:
                with open(risk_rules_path, 'r', encoding='utf-8') as f:
                    risk_rules = yaml.safe_load(f) or {}
                    self._config.setdefault('risk', {})['rules'] = risk_rules
                    logger.info(f"已加载风险规则: {risk_rules_path}")
            except Exception as e:
                logger.warning(f"加载风险规则失败: {e}")

    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'debug': False
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/codegate.log'
            },
            'paths': {
                'cache_dir': 'cache/hashes',
                'report_dir': 'reports',
                'log_dir': 'logs'
            },
            'git': {
                'clone_timeout': 300,
                'clone_depth': 2,
                'retry_attempts': 3
            },
            'claude': {
                'retry_attempts': 3,
                'retry_wait_min': 2,
                'retry_wait_max': 30
            },
            'risk': {
                'thresholds': {
                    'high': {'min': 70, 'action': 'reject'},
                    'medium': {'min': 40, 'action': 'continue'},
                    'low': {'min': 0, 'action': 'continue'}
                }
            },
            'concurrency': {
                'test_case_concurrent': 3
            }
        }

    def _merge_config(self, override: Dict):
        """
        深度合并配置

        Args:
            override: 覆盖配置字典
        """
        def merge(base: Dict, over: Dict):
            for key, value in over.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge(base[key], value)
                else:
                    base[key] = value

        merge(self._config, override)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        支持点分隔路径，如 'server.port'

        Args:
            key: 配置键，如 'server.port'
            default: 默认值

        Returns:
            配置值，不存在则返回默认值
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_risk_level(self, score: int) -> str:
        """
        根据分数获取风险等级

        Args:
            score: 风险分数 (0-100)

        Returns:
            风险等级: 'high', 'medium', 'low'
        """
        thresholds = self.get('risk.thresholds', {})

        # 按分数从高到低检查
        for level in ['high', 'medium', 'low']:
            if level in thresholds:
                min_score = thresholds[level].get('min', 0)
                if score >= min_score:
                    return level

        return 'medium'

    def get_risk_action(self, level: str) -> str:
        """
        获取风险等级对应的动作

        Args:
            level: 风险等级

        Returns:
            动作: 'reject' 或 'continue'
        """
        return self.get(f'risk.thresholds.{level}.action', 'continue')

    def reload(self):
        """重新加载配置"""
        self._config = None
        self._load_config()
        logger.info("配置已重新加载")


# 全局配置实例
config = ConfigManager()
