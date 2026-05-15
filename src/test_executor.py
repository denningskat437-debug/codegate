"""
测试用例执行模块
使用 Claude Agent SDK 并发执行测试用例校验
增强版：输出详细分析、执行时长统计、并发控制
"""
import anyio
import json
import re
import sys
import io
import time
import logging
from datetime import datetime
from typing import List, Dict

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
    from claude_agent_sdk.types import TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    logger.warning("claude_agent_sdk 未安装，测试执行功能将不可用")
    CLAUDE_SDK_AVAILABLE = False

from src.retry_handler import retry_claude_sdk
from src.config_manager import config


class TestExecutor:
    """测试用例执行器（增强版）"""

    def __init__(self, code_path: str, code_stats: Dict = None, project_type: str = None):
        """
        初始化测试执行器

        Args:
            code_path: 代码根目录路径
            code_stats: 代码统计信息（可选）
            project_type: 项目类型（可选）
        """
        self.code_path = code_path
        self.code_stats = code_stats or {}
        self.project_type = project_type or 'unknown'

    def execute_all(self, test_cases: List[Dict]) -> Dict:
        """
        并发执行所有测试用例

        Args:
            test_cases: 测试用例列表

        Returns:
            {
                'results': List[Dict],  # 各用例结果
                'time_stats': {
                    'total_time': float,
                    'average_time': float,
                    'min_time': float,
                    'max_time': float,
                    'start_time': str,
                    'end_time': str,
                    'case_count': int
                }
            }
        """
        if not test_cases:
            return {'results': [], 'time_stats': {}}

        overall_start = time.time()
        start_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 获取并发配置，动态调整
        base_concurrent = config.get('concurrency.test_case_concurrent', 10)
        total = len(test_cases)
        # 根据用例数量动态调整并发数
        if total <= 10:
            max_concurrent = min(base_concurrent, 3)
        elif total <= 50:
            max_concurrent = min(base_concurrent, 5)
        elif total <= 100:
            max_concurrent = min(base_concurrent, 8)
        else:
            max_concurrent = base_concurrent  # 100+ 用例使用配置的最大并发数

        logger.info(f"开始并发执行 {total} 个测试用例，最大并发数: {max_concurrent}")

        # 使用 anyio 运行异步并发执行
        results = anyio.run(self._execute_all_async, test_cases, max_concurrent)

        # 按原始顺序排序结果
        results.sort(key=lambda x: x.get('_index', 0))
        for r in results:
            r.pop('_index', None)

        # 统计执行时间
        execution_times = [r.get('execution_time', 0) for r in results]
        overall_end = time.time()
        end_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        time_stats = {
            'total_time': round(overall_end - overall_start, 2),
            'average_time': round(sum(execution_times) / len(execution_times), 2) if execution_times else 0,
            'min_time': round(min(execution_times), 2) if execution_times else 0,
            'max_time': round(max(execution_times), 2) if execution_times else 0,
            'start_time': start_datetime,
            'end_time': end_datetime,
            'case_count': total
        }

        passed = sum(1 for r in results if r.get('result') == 'passed')
        logger.info(f"测试执行完成: 通过 {passed}/{total}, 总耗时 {time_stats['total_time']}s")

        return {
            'results': results,
            'time_stats': time_stats
        }

    async def _execute_all_async(self, test_cases: List[Dict], max_concurrent: int) -> List[Dict]:
        """异步并发执行所有测试用例"""
        results = []
        semaphore = anyio.Semaphore(max_concurrent)
        completed = 0
        total = len(test_cases)
        lock = anyio.Lock()

        async def run_one(case: Dict, index: int):
            nonlocal completed
            async with semaphore:
                case_id = case.get('case_id', f'case_{index}')
                logger.info(f"执行测试用例 [{index}/{total}]: {case_id}")
                start_time = time.time()
                try:
                    result = await self._execute_async(case)
                    result['_index'] = index
                    result['execution_time'] = round(time.time() - start_time, 2)
                    status = "✓ 通过" if result['result'] == 'passed' else "✗ 失败"

                    async with lock:
                        completed += 1
                        progress = f"[{completed}/{total}]"
                        logger.info(f"  {status}: {case_id} (耗时 {result['execution_time']}s) {progress}")

                    results.append(result)
                except Exception as e:
                    async with lock:
                        completed += 1
                    logger.error(f"  执行异常: {case_id} - {e} [{completed}/{total}]")
                    error_result = self._error_result(case, str(e))
                    error_result['_index'] = index
                    error_result['execution_time'] = round(time.time() - start_time, 2)
                    results.append(error_result)

        async with anyio.create_task_group() as tg:
            for i, case in enumerate(test_cases, 1):
                tg.start_soon(run_one, case, i)

        return results

    def execute_one(self, case: Dict) -> Dict:
        """执行单个测试用例"""
        if not CLAUDE_SDK_AVAILABLE:
            return self._error_result(case, "Claude SDK 不可用")

        start_time = time.time()

        try:
            result = anyio.run(self._execute_async, case)
            execution_time = time.time() - start_time
            result['execution_time'] = round(execution_time, 2)
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"执行测试用例异常: {e}")
            error_result = self._error_result(case, str(e))
            error_result['execution_time'] = round(execution_time, 2)
            return error_result

    @retry_claude_sdk(max_attempts=2, wait_min=2.0, wait_max=20.0)
    async def _execute_async(self, case: Dict) -> Dict:
        """异步执行测试用例（增强版 prompt）"""
        case_id = case.get('case_id', '')
        requirement = case.get('requirement', '')
        test_point = case.get('test_point', '')
        priority = case.get('priority', '')
        precondition = case.get('precondition', '')
        steps = case.get('steps', '')
        expected = case.get('expected', '')

        # 获取项目信息
        total_lines = self.code_stats.get('total_lines', 0)
        main_languages = self.code_stats.get('main_languages', [])
        project_type = self.project_type

        prompt = f"""
你是一个专业的代码测试工程师。请根据以下测试用例对代码进行详细校验和分析。

## 项目信息
- 项目类型: {project_type}
- 代码总量: {total_lines} 行
- 主要语言: {', '.join(main_languages) if main_languages else '未知'}

## 测试用例
- 用例编号: {case_id}
- 对应需求: {requirement}
- 测试点: {test_point}
- 优先级: {priority}
- 前置条件: {precondition}
- 操作步骤: {steps}
- 预期结果: {expected}

## 分析要求
请仔细分析代码，执行以下检查：

1. **测试结果判断**: 代码是否实现了预期功能？passed 或 failed
2. **校验依据**: 说明如何验证的，引用具体代码位置
3. **问题代码**: 如果失败，指出具体问题代码位置
4. **项目类型匹配分析**: 测试用例是否与项目类型匹配？分析合理性
5. **前端问题**: 发现的前端相关问题（如有）
6. **后端问题**: 发现的后端相关问题（如有）
7. **关键证据**: 支持结论的代码证据（具体文件和行号）
8. **优劣势分析**: 代码实现的优点和缺点
9. **综合结论**: 给出最终分析结论
10. **潜在问题**: 指出可能存在的潜在问题及证据

请按以下 JSON 格式输出（只输出JSON，不要其他内容）：
{{
    "result": "passed 或 failed",
    "evidence": "校验依据说明，引用具体代码位置",
    "problem_code": "问题代码位置（失败时填写）",
    "analysis": {{
        "project_type_match": {{
            "actual_type": "{project_type}",
            "match_score": 0.0-1.0,
            "analysis": "匹配分析说明"
        }},
        "frontend_issues": [
            {{"issue": "问题描述", "location": "文件位置", "evidence": "代码证据"}}
        ],
        "backend_issues": [
            {{"issue": "问题描述", "location": "文件位置", "evidence": "代码证据"}}
        ],
        "key_evidence": [
            "证据1：具体代码位置和内容",
            "证据2：具体代码位置和内容"
        ],
        "strengths": [
            "优点1",
            "优点2"
        ],
        "weaknesses": [
            "缺点1",
            "缺点2"
        ],
        "conclusion": "综合分析结论",
        "potential_issues": [
            {{"issue": "潜在问题", "probability": "高/中/低", "evidence": "证据"}}
        ]
    }}
}}

注意：
- result 只能是 "passed" 或 "failed"
- evidence 必须引用具体代码位置（文件名:行号）
- 如果测试通过，problem_code 为空字符串
- analysis 中的所有字段都要填写，即使为空数组也要保留
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
        """解析结果（增强版）"""
        try:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())
                result.setdefault('result', 'failed')
                result.setdefault('evidence', '')
                result.setdefault('problem_code', '')
                result.setdefault('analysis', {
                    'project_type_match': {'actual_type': '', 'match_score': 0, 'analysis': ''},
                    'frontend_issues': [],
                    'backend_issues': [],
                    'key_evidence': [],
                    'strengths': [],
                    'weaknesses': [],
                    'conclusion': '',
                    'potential_issues': []
                })

                if result['result'] not in ['passed', 'failed']:
                    result['result'] = 'failed'

                return result

        except json.JSONDecodeError:
            pass

        return {
            "result": "failed",
            "evidence": text[:500] if text else "无法解析结果",
            "problem_code": "",
            "analysis": {
                'project_type_match': {'actual_type': '', 'match_score': 0, 'analysis': '解析失败'},
                'frontend_issues': [],
                'backend_issues': [],
                'key_evidence': [],
                'strengths': [],
                'weaknesses': [],
                'conclusion': '结果解析失败',
                'potential_issues': []
            }
        }

    def _error_result(self, case: Dict, error: str) -> Dict:
        """生成错误结果"""
        return {
            'case_id': case.get('case_id', ''),
            'result': 'failed',
            'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'execution_time': 0,
            'requirement': case.get('requirement', ''),
            'test_point': case.get('test_point', ''),
            'priority': case.get('priority', ''),
            'evidence': f"执行异常: {error}",
            'problem_code': '',
            'analysis': {
                'project_type_match': {'actual_type': '', 'match_score': 0, 'analysis': f'执行异常: {error}'},
                'frontend_issues': [],
                'backend_issues': [],
                'key_evidence': [],
                'strengths': [],
                'weaknesses': [],
                'conclusion': f'执行异常: {error}',
                'potential_issues': []
            }
        }
