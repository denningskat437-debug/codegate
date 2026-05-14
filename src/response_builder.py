"""
响应构建模块
构建统一的 API 响应格式
"""
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """响应构建器"""

    # 错误码定义
    ERROR_CODES = {
        0: '成功',
        1: '检测失败',
        1001: '参数缺失',
        1002: '参数格式错误',
        2001: '测试用例文件不存在',
        2002: '测试用例文件格式错误',
        5001: '服务器内部错误',
        5002: 'Git 操作失败',
        5003: 'AI 分析异常',
    }

    @staticmethod
    def success(message: str, data: Dict = None) -> Dict:
        """
        构建成功响应

        Args:
            message: 成功消息
            data: 响应数据

        Returns:
            响应字典
        """
        response = {
            'code': 0,
            'message': message
        }
        if data:
            response['data'] = data
        return response

    @staticmethod
    def error(code: int, message: str = None, details: str = None) -> Dict:
        """
        构建错误响应

        Args:
            code: 错误码
            message: 错误消息（可选，默认使用错误码定义）
            details: 详细信息

        Returns:
            响应字典
        """
        if message is None:
            message = ResponseBuilder.ERROR_CODES.get(code, '未知错误')

        response = {
            'code': code,
            'message': message
        }
        if details:
            response['details'] = details
        return response

    @staticmethod
    def risk_reject(risk_result: Dict, report_url: str = None) -> Dict:
        """
        构建高风险打回响应

        Args:
            risk_result: 风险评估结果
            report_url: 报告URL

        Returns:
            响应字典
        """
        response = {
            'code': 1,
            'message': '高风险代码，已打回',
            'risk': {
                'level': risk_result.get('level', 'high'),
                'score': risk_result.get('score', 0),
                'items': risk_result.get('items', []),
                'summary': risk_result.get('summary', '')
            }
        }
        if report_url:
            response['report_url'] = report_url
        return response

    @staticmethod
    def test_result(
        test_results: List[Dict],
        all_passed: bool,
        report_url: str = None
    ) -> Dict:
        """
        构建测试结果响应

        Args:
            test_results: 测试结果列表
            all_passed: 是否全部通过
            report_url: 报告URL

        Returns:
            响应字典
        """
        total = len(test_results)
        passed = sum(1 for r in test_results if r.get('result') == 'passed')
        failed = total - passed

        response = {
            'code': 0 if all_passed else 1,
            'message': '全部通过，可进入提测' if all_passed else '存在失败用例，不可进入提测',
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'pass_rate': f"{passed/total*100:.1f}%" if total > 0 else "0%"
            },
            'results': test_results
        }
        if report_url:
            response['report_url'] = report_url
        return response

    @staticmethod
    def no_change() -> Dict:
        """
        构建代码未变化响应

        Returns:
            响应字典
        """
        return {
            'code': 0,
            'message': '代码未变化，无需检测'
        }