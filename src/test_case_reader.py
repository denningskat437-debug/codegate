"""
测试用例读取模块
从 xlsx 文件读取测试用例
"""
import pandas as pd
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class TestCaseReader:
    """测试用例读取器"""

    # 必需的列名
    REQUIRED_COLUMNS = ['用例编号']

    # 支持的列名映射
    COLUMN_MAPPINGS = {
        '用例编号': 'case_id',
        '对应需求': 'requirement',
        '测试点': 'test_point',
        '优先级': 'priority',
        '前置条件': 'precondition',
        '操作步骤': 'steps',
        '预期结果': 'expected'
    }

    def __init__(self, file_path: str):
        """
        初始化测试用例读取器

        Args:
            file_path: xlsx 文件路径
        """
        self.file_path = Path(file_path)

    def read(self) -> List[Dict]:
        """
        读取 xlsx 测试用例

        Returns:
            测试用例列表，每个用例包含：
            - case_id: 用例编号
            - requirement: 对应需求
            - test_point: 测试点
            - priority: 优先级
            - precondition: 前置条件
            - steps: 操作步骤
            - expected: 预期结果

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        # 检查文件是否存在
        if not self.file_path.exists():
            raise FileNotFoundError(f"测试用例文件不存在: {self.file_path}")

        # 检查文件扩展名
        if self.file_path.suffix.lower() not in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}")

        try:
            # 读取 Excel 文件
            df = pd.read_excel(self.file_path)
            logger.info(f"读取到 {len(df)} 条测试用例")

            # 检查必需列
            missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必需列: {missing_columns}")

            # 转换为字典列表
            test_cases = []
            for idx, row in df.iterrows():
                case = {}
                for cn_name, en_name in self.COLUMN_MAPPINGS.items():
                    if cn_name in df.columns:
                        value = row.get(cn_name, '')
                        # 处理 NaN 值
                        if pd.isna(value):
                            value = ''
                        case[en_name] = str(value).strip()
                    else:
                        case[en_name] = ''

                # 确保用例编号不为空
                if case['case_id']:
                    test_cases.append(case)
                    logger.debug(f"读取用例: {case['case_id']} - {case['test_point']}")

            logger.info(f"成功读取 {len(test_cases)} 条有效测试用例")
            return test_cases

        except pd.errors.EmptyDataError:
            raise ValueError(f"测试用例文件为空: {self.file_path}")
        except Exception as e:
            raise ValueError(f"读取测试用例失败: {e}")

    def validate(self, test_cases: List[Dict]) -> List[str]:
        """
        验证测试用例完整性

        Args:
            test_cases: 测试用例列表

        Returns:
            验证问题列表，空列表表示验证通过
        """
        issues = []

        for i, case in enumerate(test_cases):
            case_id = case.get('case_id', f'第{i+1}行')

            # 检查必需字段
            if not case.get('test_point'):
                issues.append(f"{case_id}: 缺少测试点")

            if not case.get('steps'):
                issues.append(f"{case_id}: 缺少操作步骤")

            if not case.get('expected'):
                issues.append(f"{case_id}: 缺少预期结果")

        return issues
