"""
TestCaseReader 单元测试
测试测试用例读取模块的所有公共方法
"""
import pytest
from pathlib import Path
from src.test_case_reader import TestCaseReader


class TestTestCaseReaderInit:
    """测试初始化"""

    def test_init_with_valid_path(self, sample_test_case_file):
        """测试有效路径初始化"""
        reader = TestCaseReader(sample_test_case_file)
        assert reader.file_path == Path(sample_test_case_file)

    def test_init_with_nonexistent_path(self):
        """测试不存在路径初始化（不立即检查）"""
        reader = TestCaseReader('/nonexistent/path.xlsx')
        assert reader.file_path == Path('/nonexistent/path.xlsx')


class TestTestCaseReaderRead:
    """测试 read 方法"""

    def test_read_valid_file(self, sample_test_case_file):
        """测试读取有效测试用例文件"""
        reader = TestCaseReader(sample_test_case_file)
        cases = reader.read()

        assert len(cases) == 3
        assert cases[0]['case_id'] == 'TC001'
        assert cases[0]['requirement'] == '用户登录'
        assert cases[0]['test_point'] == '登录验证'
        assert cases[0]['priority'] == 'P0'

    def test_read_file_not_found(self):
        """测试读取不存在的文件"""
        reader = TestCaseReader('/nonexistent/test.xlsx')
        with pytest.raises(FileNotFoundError):
            reader.read()

    def test_read_invalid_extension(self, temp_dir):
        """测试无效文件扩展名"""
        invalid_file = Path(temp_dir) / 'test.txt'
        invalid_file.write_text('test')

        reader = TestCaseReader(str(invalid_file))
        with pytest.raises(ValueError, match='不支持的文件格式'):
            reader.read()

    def test_read_missing_required_column(self, invalid_test_case_file):
        """测试缺少必需列"""
        reader = TestCaseReader(invalid_test_case_file)
        with pytest.raises(ValueError, match='缺少必需列'):
            reader.read()

    def test_read_empty_file(self, empty_test_case_file):
        """测试空文件"""
        reader = TestCaseReader(empty_test_case_file)
        with pytest.raises(ValueError, match='缺少必需列'):
            reader.read()

    def test_read_handles_nan_values(self, temp_dir):
        """测试处理 NaN 值"""
        import pandas as pd

        # 创建包含 NaN 的文件
        df = pd.DataFrame({
            '用例编号': ['TC001', 'TC002'],
            '测试点': ['登录', None],  # NaN 值
            '操作步骤': ['步骤1', '步骤2'],
            '预期结果': ['结果1', '结果2']
        })
        file_path = Path(temp_dir) / 'nan_test.xlsx'
        df.to_excel(file_path, index=False)

        reader = TestCaseReader(str(file_path))
        cases = reader.read()

        assert len(cases) == 2
        assert cases[1]['test_point'] == ''  # NaN 应转为空字符串

    def test_read_strips_whitespace(self, temp_dir):
        """测试去除空白字符"""
        import pandas as pd

        df = pd.DataFrame({
            '用例编号': ['TC001'],
            '测试点': ['  登录功能  '],  # 带空格
            '操作步骤': ['步骤'],
            '预期结果': ['结果']
        })
        file_path = Path(temp_dir) / 'whitespace_test.xlsx'
        df.to_excel(file_path, index=False)

        reader = TestCaseReader(str(file_path))
        cases = reader.read()

        assert cases[0]['test_point'] == '登录功能'  # 空格被去除


class TestTestCaseReaderValidate:
    """测试 validate 方法"""

    def test_validate_valid_cases(self):
        """测试验证有效的测试用例"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '登录验证',
                'steps': '输入用户名密码',
                'expected': '登录成功'
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 0

    def test_validate_missing_test_point(self):
        """测试缺少测试点"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '',
                'steps': '步骤',
                'expected': '结果'
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 1
        assert '缺少测试点' in issues[0]

    def test_validate_missing_steps(self):
        """测试缺少操作步骤"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '测试点',
                'steps': '',
                'expected': '结果'
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 1
        assert '缺少操作步骤' in issues[0]

    def test_validate_missing_expected(self):
        """测试缺少预期结果"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '测试点',
                'steps': '步骤',
                'expected': ''
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 1
        assert '缺少预期结果' in issues[0]

    def test_validate_multiple_issues(self):
        """测试多个问题"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '',
                'steps': '',
                'expected': ''
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 3

    def test_validate_multiple_cases(self):
        """测试多个用例的验证"""
        cases = [
            {
                'case_id': 'TC001',
                'test_point': '测试点1',
                'steps': '步骤1',
                'expected': '结果1'
            },
            {
                'case_id': 'TC002',
                'test_point': '',  # 缺少
                'steps': '步骤2',
                'expected': '结果2'
            }
        ]
        reader = TestCaseReader('dummy.xlsx')
        issues = reader.validate(cases)
        assert len(issues) == 1
        assert 'TC002' in issues[0]


class TestTestCaseReaderColumnMappings:
    """测试列名映射"""

    def test_all_column_mappings(self, sample_test_case_file):
        """测试所有列名正确映射"""
        reader = TestCaseReader(sample_test_case_file)
        cases = reader.read()

        case = cases[0]
        # 检查所有映射字段存在
        assert 'case_id' in case
        assert 'requirement' in case
        assert 'test_point' in case
        assert 'priority' in case
        assert 'precondition' in case
        assert 'steps' in case
        assert 'expected' in case

    def test_optional_columns_missing(self, temp_dir):
        """测试可选列缺失时使用默认值"""
        import pandas as pd

        df = pd.DataFrame({
            '用例编号': ['TC001'],
            '测试点': ['测试点'],
            '操作步骤': ['步骤'],
            '预期结果': ['结果']
            # 缺少 对应需求、优先级、前置条件
        })
        file_path = Path(temp_dir) / 'minimal.xlsx'
        df.to_excel(file_path, index=False)

        reader = TestCaseReader(str(file_path))
        cases = reader.read()

        assert cases[0]['requirement'] == ''
        assert cases[0]['priority'] == ''
        assert cases[0]['precondition'] == ''
