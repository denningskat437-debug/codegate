"""
AI 风险评估模块
使用 Claude Agent SDK 对代码进行安全风险分析
"""
import anyio
import json
import re
import logging
import sys
import io
from typing import Dict, List

# 设置标准输出为 UTF-8 编码，解决 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

# 延迟导入 Claude Agent SDK
try:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
    from claude_agent_sdk.types import TextBlock
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    logger.warning("claude_agent_sdk 未安装，AI 风险评估功能将不可用")
    CLAUDE_SDK_AVAILABLE = False


class AIRiskAnalyzer:
    """AI 风险评估器 - 使用 Claude Agent SDK"""

    def __init__(self, code_path: str):
        """
        初始化风险评估器

        Args:
            code_path: 代码根目录路径
        """
        self.code_path = code_path

    def analyze(self) -> Dict:
        """
        执行风险评估

        Returns:
            包含 level, score, items, summary 的字典
        """
        if not CLAUDE_SDK_AVAILABLE:
            logger.warning("Claude SDK 不可用，返回默认中等风险")
            return self._default_result("Claude SDK 不可用")

        try:
            return anyio.run(self._analyze_async)
        except Exception as e:
            logger.error(f"AI 风险评估异常: {e}")
            return self._default_result(str(e))

    async def _analyze_async(self) -> Dict:
        """异步执行风险评估"""
        prompt = """
请对代码进行全面安全风险检查：

1. SQL 注入风险 - 检查是否存在拼接SQL语句、未使用参数化查询
2. XSS 跨站脚本攻击 - 检查是否转义用户输入、是否使用 innerHTML
3. 敏感信息泄露 - 检查是否有硬编码密码、API Key、Token、密钥
4. 命令注入风险 - 检查是否执行用户输入的命令、使用 eval/exec
5. 权限校验缺失 - 检查是否有未校验权限的接口、越权访问风险

请仔细分析代码，按以下 JSON 格式输出评估结果（只输出JSON，不要其他内容）：
{
    "level": "medium",
    "score": 35,
    "items": [
        {
            "type": "sql_injection",
            "location": "app/db.py:45",
            "description": "存在SQL拼接，可能导致注入攻击"
        }
    ],
    "summary": "发现SQL注入风险，建议使用参数化查询"
}

注意：分数范围 0-100，分数越高风险越大。
- 0-39: 低风险 (level: "low")
- 40-69: 中风险 (level: "medium")
- 70-100: 高风险 (level: "high")
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
                            logger.debug(f"Claude 输出: {block.text[:100]}...")
        except Exception as e:
            logger.error(f"Claude SDK 调用异常: {e}")
            return self._default_result(str(e))

        return self._parse_result(result_text)

    def _parse_result(self, text: str) -> Dict:
        """
        解析 AI 返回结果

        Args:
            text: AI 返回的文本

        Returns:
            解析后的结果字典
        """
        try:
            # 尝试提取 JSON
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                result = json.loads(match.group())

                # 确保必要字段存在
                result.setdefault('level', 'medium')
                result.setdefault('score', 50)
                result.setdefault('items', [])
                result.setdefault('summary', '')

                # 验证 level 值
                if result['level'] not in ['high', 'medium', 'low']:
                    result['level'] = 'medium'

                # 验证 score 范围
                result['score'] = max(0, min(100, int(result['score'])))

                logger.info(f"AI 风险评估完成: level={result['level']}, score={result['score']}")
                return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")

        # 解析失败时返回默认结果
        return self._default_result(text[:200] if text else "无法解析评估结果")

    def _default_result(self, reason: str) -> Dict:
        """
        生成默认结果

        Args:
            reason: 原因说明

        Returns:
            默认结果字典
        """
        return {
            "level": "medium",
            "score": 50,
            "items": [],
            "summary": f"评估异常: {reason}"
        }
