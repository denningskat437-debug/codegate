"""
测试用例执行模块
使用 Claude Agent SDK 逐条执行测试用例校验
"""
import anyio
import json
import re
import sys
import io
import logging
from datetime import datetime
from typing import List, Dict

# 设置标准输出为 UTF-8 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

# 延迟导入 Claude Agent SDK
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
    from claude_agent_sdk.types import TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    logger.warning("claude_agent_sdk 未安装，测试执行功能将不可用")
    CLAUDE_SDK_AVAILABLE = False


class TestExecutor:
    """测试用例执行器"""

    def __init__(self, code_path: str):
        """
        初始化测试执行器

        Args:
            code_path: 代码根目录路径
        """
        self.code_path = code_path

    def execute_all(self, test_cases: List[Dict]) -> List[Dict]:
        """
        执行所有测试用例

        Args:
            test_cases: 测试用例列表

        Returns:
            测试结果列表
        """
        results = []
        total = len(test_cases)

        for i, case in enumerate(test_cases, 1):
            case_id = case.get('case_id', f'case_{i}')
            logger.info(f"执行测试用例 [{i}/{total}]: {case_id}")

            try:
                result = self.execute_one(case)
                results.append(result)

                status = "✓ 通过" if result['result'] == 'passed' else "✗ 失败"
                logger.info(f"  {status}: {case_id}")

            except Exception as e:
                logger.error(f"  执行异常: {case_id} - {e}")
                results.append(self._error_result(case, str(e)))

        return results

    def execute_one(self, case: Dict) -> Dict:
        """
        执行单个测试用例

        Args:
            case: 测试用例字典

        Returns:
            测试结果字典
        """
        if not CLAUDE_SDK_AVAILABLE:
            return self._error_result(case, "Claude SDK 不可用")

        try:
            return anyio.run(self._execute_async, case)
        except Exception as e:
            logger.error(f"执行测试用例异常: {e}")
            return self._error_result(case, str(e))

    async def _execute_async(self, case: Dict) -> Dict:
        """异步执行测试用例"""
        case_id = case.get('case_id', '')
        requirement = case.get('requirement', '')
        test_point = case.get('test_point', '')
        priority = case.get('priority', '')
        precondition = case.get('precondition', '')
        steps = case.get('steps', '')
        expected = case.get('expected', '')

        prompt = f"""
请检查代码是否满足以下测试用例要求：

【用例编号】{case_id}
【对应需求】{requirement}
【测试点】{test_point}
【优先级】{priority}
【前置条件】{precondition}
【操作步骤】{steps}
【预期结果】{expected}

请仔细分析代码，判断是否实现了该测试用例的要求。
如果代码实现了预期功能，结果为 passed；否则为 failed。

输出 JSON 格式（只输出JSON，不要其他内容）：
{{
    "result": "passed",
    "evidence": "代码中 xxx 函数实现了 xxx 功能，位于 xxx.py 第 xx 行",
    "problem_code": ""
}}

如果失败：
{{
    "result": "failed",
    "evidence": "未找到 xxx 功能的实现，代码中缺少 xxx",
    "problem_code": "app/xxx.py 缺少 xxx 方法"
}}
"""

        options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            permission_mode="acceptEdits",
            cwd=self.code_path
        )

        result_text = ""
        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            result_text += block.text
        except Exception as e:
            logger.error(f"Claude SDK 调用异常: {e}")
            return self._error_result(case, str(e))

        result = self._parse_result(result_text)
        result['case_id'] = case_id
        result['test_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result['requirement'] = requirement
        result['test_point'] = test_point
        result['priority'] = priority

        return result

    def _parse_result(self, text: str) -> Dict:
        """解析结果"""
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                result.setdefault('result', 'failed')
                result.setdefault('evidence', '')
                result.setdefault('problem_code', '')

                # 验证 result 值
                if result['result'] not in ['passed', 'failed']:
                    result['result'] = 'failed'

                return result

        except json.JSONDecodeError:
            pass

        return {
            "result": "failed",
            "evidence": text[:500] if text else "无法解析结果",
            "problem_code": ""
        }

    def _error_result(self, case: Dict, error: str) -> Dict:
        """生成错误结果"""
        return {
            'case_id': case.get('case_id', ''),
            'result': 'failed',
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'requirement': case.get('requirement', ''),
            'test_point': case.get('test_point', ''),
            'priority': case.get('priority', ''),
            'evidence': f"执行异常: {error}",
            'problem_code': ''
        }
