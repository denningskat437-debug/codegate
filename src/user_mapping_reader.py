"""
用户映射读取模块
从 xlsx 文件读取用户名到邮箱的映射
"""
import pandas as pd
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class UserMappingReader:
    """用户映射读取器"""

    REQUIRED_COLUMNS = ['用户名']

    def __init__(self, file_path: str):
        """
        初始化用户映射读取器

        Args:
            file_path: xlsx 文件路径
        """
        self.file_path = Path(file_path)
        self._mapping_cache: Dict[str, str] = None

    def read(self) -> Dict[str, str]:
        """
        读取用户映射

        Returns:
            用户名到邮箱的映射字典

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"用户映射文件不存在: {self.file_path}")

        if self.file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}")

        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"读取到 {len(df)} 条用户映射")

            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必需列: {missing_columns}")

            mapping = {}
            for idx, row in df.iterrows():
                username = str(row.get('用户名', '')).strip()
                email = str(row.get('邮箱', '')).strip() if '邮箱' in df.columns else ''

                if pd.isna(username) or not username:
                    continue
                if pd.isna(email):
                    email = ''

                if username and email:
                    mapping[username] = email
                    logger.debug(f"用户映射: {username} -> {email}")

            logger.info(f"成功读取 {len(mapping)} 条有效用户映射")
            return mapping

        except pd.errors.EmptyDataError:
            raise ValueError(f"用户映射文件为空: {self.file_path}")
        except Exception as e:
            raise ValueError(f"读取用户映射失败: {e}")

    def get_email(self, username: str) -> Optional[str]:
        """
        根据用户名获取邮箱

        Args:
            username: 用户名

        Returns:
            邮箱地址，不存在则返回 None
        """
        if self._mapping_cache is None:
            self._mapping_cache = self.read()

        return self._mapping_cache.get(username)

    def reload(self) -> None:
        """重新加载映射缓存"""
        self._mapping_cache = None
        logger.info("用户映射缓存已清除")