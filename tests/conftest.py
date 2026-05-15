"""
pytest 共享 fixtures
提供测试所需的公共资源和配置
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """临时目录 fixture，测试结束后自动清理"""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def sample_test_case_file(temp_dir):
    """创建示例测试用例 Excel 文件"""
    import pandas as pd

    df = pd.DataFrame({
        '用例编号': ['TC001', 'TC002', 'TC003'],
        '对应需求': ['用户登录', '用户登录', '会话管理'],
        '测试点': ['登录验证', '密码加密', 'Session超时'],
        '优先级': ['P0', 'P0', 'P1'],
        '前置条件': ['用户已注册', '用户已注册', '用户已登录'],
        '操作步骤': ['输入用户名密码点击登录', '检查密码存储方式', '等待30分钟'],
        '预期结果': ['登录成功', '密码已加密存储', 'Session过期']
    })

    file_path = Path(temp_dir) / 'test_cases.xlsx'
    df.to_excel(file_path, index=False)
    return str(file_path)


@pytest.fixture
def empty_test_case_file(temp_dir):
    """创建空的测试用例文件"""
    file_path = Path(temp_dir) / 'empty.xlsx'
    import pandas as pd
    df = pd.DataFrame()
    df.to_excel(file_path, index=False)
    return str(file_path)


@pytest.fixture
def invalid_test_case_file(temp_dir):
    """创建缺少必需列的测试用例文件"""
    file_path = Path(temp_dir) / 'invalid.xlsx'
    import pandas as pd
    df = pd.DataFrame({
        '测试点': ['登录功能'],
        '预期结果': ['登录成功']
    })
    df.to_excel(file_path, index=False)
    return str(file_path)


@pytest.fixture
def sample_code_dir(temp_dir):
    """创建示例代码目录"""
    code_dir = Path(temp_dir) / 'sample_code'
    code_dir.mkdir(parents=True, exist_ok=True)

    # 创建示例 Python 文件
    (code_dir / 'main.py').write_text('print("hello world")')
    (code_dir / 'utils.py').write_text('def helper(): return True')

    return str(code_dir)