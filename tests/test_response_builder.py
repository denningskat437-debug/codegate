"""
ResponseBuilder 单元测试
测试响应构建模块的所有公共方法
"""
import pytest
from src.response_builder import ResponseBuilder


class TestResponseBuilderSuccess:
    """测试 success 方法"""

    def test_success_basic(self):
        """测试基本成功响应"""
        result = ResponseBuilder.success("操作成功")
        assert result['code'] == 0
        assert result['message'] == "操作成功"
        assert 'data' not in result

    def test_success_with_data(self):
        """测试带数据的成功响应"""
        data = {'key': 'value', 'count': 10}
        result = ResponseBuilder.success("成功", data)
        assert result['code'] == 0
        assert result['message'] == "成功"
        assert result['data'] == data

    def test_success_with_empty_data(self):
        """测试带空数据的成功响应 - 空字典被视为 falsy，不添加 data 字段"""
        result = ResponseBuilder.success("成功", {})
        # 空字典 {} 是 falsy，所以不会添加 data 字段
        assert 'data' not in result


class TestResponseBuilderError:
    """测试 error 方法"""

    def test_error_with_predefined_code(self):
        """测试使用预定义错误码"""
        result = ResponseBuilder.error(1001)
        assert result['code'] == 1001
        assert '参数缺失' in result['message']

    def test_error_with_custom_message(self):
        """测试自定义错误消息"""
        result = ResponseBuilder.error(1001, "自定义错误消息")
        assert result['code'] == 1001
        assert result['message'] == "自定义错误消息"

    def test_error_with_details(self):
        """测试带详细信息的错误响应"""
        result = ResponseBuilder.error(5001, "服务器错误", "详细堆栈信息")
        assert result['code'] == 5001
        assert result['message'] == "服务器错误"
        assert result['details'] == "详细堆栈信息"

    def test_error_unknown_code(self):
        """测试未知错误码"""
        result = ResponseBuilder.error(9999)
        assert result['code'] == 9999
        assert '未知错误' in result['message']


class TestResponseBuilderRiskReject:
    """测试 risk_reject 方法"""

    def test_risk_reject_basic(self):
        """测试基本高风险打回响应"""
        risk_result = {
            'level': 'high',
            'score': 85,
            'items': [{'type': 'sql_injection', 'location': 'db.py:10'}],
            'summary': '发现SQL注入风险'
        }
        result = ResponseBuilder.risk_reject(risk_result)
        assert result['code'] == 1
        assert result['message'] == '高风险代码，已打回'
        assert result['risk']['level'] == 'high'
        assert result['risk']['score'] == 85
        assert len(result['risk']['items']) == 1

    def test_risk_reject_with_report_url(self):
        """测试带报告URL的高风险打回响应"""
        risk_result = {'level': 'high', 'score': 90, 'items': [], 'summary': 'test'}
        result = ResponseBuilder.risk_reject(risk_result, '/reports/TASK001/report.json')
        assert result['report_url'] == '/reports/TASK001/report.json'

    def test_risk_reject_missing_fields(self):
        """测试缺少字段的风险结果"""
        risk_result = {}
        result = ResponseBuilder.risk_reject(risk_result)
        assert result['risk']['level'] == 'high'
        assert result['risk']['score'] == 0
        assert result['risk']['items'] == []


class TestResponseBuilderTestResult:
    """测试 test_result 方法"""

    def test_test_result_all_passed(self):
        """测试全部通过的测试结果"""
        results = [
            {'case_id': 'TC001', 'result': 'passed'},
            {'case_id': 'TC002', 'result': 'passed'},
            {'case_id': 'TC003', 'result': 'passed'}
        ]
        response = ResponseBuilder.test_result(results, True)
        assert response['code'] == 0
        assert response['message'] == '全部通过，可进入提测'
        assert response['summary']['total'] == 3
        assert response['summary']['passed'] == 3
        assert response['summary']['failed'] == 0
        assert response['summary']['pass_rate'] == '100.0%'

    def test_test_result_some_failed(self):
        """测试部分失败的测试结果"""
        results = [
            {'case_id': 'TC001', 'result': 'passed'},
            {'case_id': 'TC002', 'result': 'failed'},
            {'case_id': 'TC003', 'result': 'passed'}
        ]
        response = ResponseBuilder.test_result(results, False)
        assert response['code'] == 1
        assert response['message'] == '存在失败用例，不可进入提测'
        assert response['summary']['total'] == 3
        assert response['summary']['passed'] == 2
        assert response['summary']['failed'] == 1
        assert response['summary']['pass_rate'] == '66.7%'

    def test_test_result_all_failed(self):
        """测试全部失败的测试结果"""
        results = [
            {'case_id': 'TC001', 'result': 'failed'},
            {'case_id': 'TC002', 'result': 'failed'}
        ]
        response = ResponseBuilder.test_result(results, False)
        assert response['code'] == 1
        assert response['summary']['pass_rate'] == '0.0%'

    def test_test_result_empty(self):
        """测试空结果列表"""
        results = []
        response = ResponseBuilder.test_result(results, True)
        assert response['summary']['total'] == 0
        assert response['summary']['pass_rate'] == '0%'

    def test_test_result_with_report_url(self):
        """测试带报告URL的测试结果"""
        results = [{'result': 'passed'}]
        response = ResponseBuilder.test_result(results, True, '/reports/TASK001/report.json')
        assert response['report_url'] == '/reports/TASK001/report.json'


class TestResponseBuilderNoChange:
    """测试 no_change 方法"""

    def test_no_change(self):
        """测试代码未变化响应"""
        result = ResponseBuilder.no_change()
        assert result['code'] == 0
        assert result['message'] == '代码未变化，无需检测'


class TestResponseBuilderErrorCodes:
    """测试错误码定义"""

    def test_error_codes_defined(self):
        """测试预定义错误码存在"""
        codes = ResponseBuilder.ERROR_CODES
        assert 0 in codes  # 成功
        assert 1001 in codes  # 参数缺失
        assert 2001 in codes  # 测试用例文件不存在
        assert 5001 in codes  # 服务器内部错误

    def test_error_codes_messages(self):
        """测试错误码消息"""
        codes = ResponseBuilder.ERROR_CODES
        assert '成功' in codes[0]
        assert '参数缺失' in codes[1001]
