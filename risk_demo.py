import anyio
import sys
import io
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
from claude_agent_sdk.types import TextBlock, ThinkingBlock, ToolUseBlock

# 设置标准输出为 UTF-8 编码，解决 Windows 控制台 emoji 显示问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def check_feature_with_sdk(code_path: str, test_case: str) -> None:
    """
    使用 Claude Agent SDK 检查指定源码中某个功能是否已实现。

    Args:
        code_path: 要检查的源代码根目录的路径（例如项目根目录）。
        test_case: 请检查代码中是否存在安全风险，如SQL注入、XSS、敏感信息泄露等

    Returns:
        None，结果会直接打印到控制台。
    """
    # 构造发送给 Claude 的提示词，明确要求分析代码路径和测试用例
    prompt = (
      f"请对以下路径的代码进行全面的安全风险检查：'{code_path}'。"
      f"检查重点：{test_case}。"
      f"请检查以下安全问题："
      f"1. SQL注入风险"
      f"2. XSS跨站脚本攻击"
      f"3. 敏感信息泄露（硬编码密码、API密钥等）"
      f"4. 命令注入风险"
      f"5. 不安全的依赖或配置"
      f"对每个发现的问题，请说明风险等级、具体位置和修复建议。"
      f"1. SQL注入风险"
      f"2. XSS跨站脚本攻击"
      f"3. 敏感信息泄露（硬编码密码、API密钥等）"
      f"4. 命令注入风险"
      f"5. 不安全的依赖或配置"
      f"对每个发现的问题，请说明风险等级、具体位置和修复建议。"
  )

    # 配置 Claude Agent 选项
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep"],   # 允许使用的工具：读取文件、文件模式搜索、内容搜索
        permission_mode="acceptEdits",            # 权限模式：接受编辑（此处仅用于分析，不会实际修改）
        cwd=code_path                             # 设置工作目录为代码根路径
    )

    # 发起查询并异步迭代响应消息
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    # 实时输出 Claude 返回的文本分析结果
                    print(block.text, end="")
                elif isinstance(block, ThinkingBlock):
                    # 可选择性输出思考过程（此处简单标记）
                    print("\n[思考过程]", end="")
                elif isinstance(block, ToolUseBlock):
                    # 输出工具调用信息，便于了解 Claude 使用了哪些工具
                    print(f"\n[调用工具: {block.name}]", end="")
                else:
                    # 未知类型块的处理（防御性编程）
                    print(f"\n[未知块类型: {type(block).__name__}]", end="")
    print()  # 最后输出换行，保证输出整洁

async def main() -> None:
    """
    主函数：调用检查功能，传入要分析的项目路径和具体的测试用例描述。
    """
    await check_feature_with_sdk(
        code_path="D:/test/demo/data-analysis-demo",
        test_case="请检查代码中是否存在安全风险，如SQL注入、XSS、敏感信息泄露等？"
    )

if __name__ == "__main__":
    # 使用 anyio 运行异步主函数
    anyio.run(main)